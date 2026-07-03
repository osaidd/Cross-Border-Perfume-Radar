import argparse
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor

FEATURE_COLS = ["brand", "line", "name", "size_ml", "concentration"]


def _normalize_str(x: str) -> str:
	return str(x).strip().lower()


def _key(df: pd.DataFrame) -> pd.Series:
	return (
		df["brand"].map(_normalize_str)
		+ "|" + df["line"].map(_normalize_str)
		+ "|" + df["name"].map(_normalize_str)
		+ "|" + df["size_ml"].astype(int).astype(str)
		+ "|" + df["concentration"].map(_normalize_str)
	)


def prepare_training_pairs(wholesale_df: pd.DataFrame, retail_df: pd.DataFrame) -> pd.DataFrame:
	wk = _key(wholesale_df)
	rk = _key(retail_df)
	w = wholesale_df.copy()
	r = retail_df.copy()
	w["_key"] = wk
	r["_key"] = rk
	pairs = pd.merge(w, r[["_key", "retail_aed"]], on="_key", how="inner")
	pairs = pairs[(pairs["retail_aed"].notna()) & (pairs["wholesale_aed"].notna())]
	pairs["ratio"] = pairs["wholesale_aed"] / pairs["retail_aed"].replace({0: np.nan})
	pairs = pairs.replace([np.inf, -np.inf], np.nan).dropna(subset=["ratio"]) 
	return pairs


def encode_features(df: pd.DataFrame) -> pd.DataFrame:
	X = pd.get_dummies(
		df[["brand", "line", "concentration"]].map(lambda s: str(s).strip().lower())
	)
	X["size_ml"] = df["size_ml"].astype(float).fillna(0)
	return X


def _pick_ratio(brand, line, ratio_by_brand_line, ratio_by_brand, ratio_global):
	cand = ratio_by_brand_line.get((brand, line))
	if cand is None:
		cand = ratio_by_brand.get(brand)
	if cand is None:
		cand = ratio_global
	return float(cand)


def train_models(pairs: pd.DataFrame):
	# Ratio estimator (brand- and brand-line-level medians)
	ratio_global = pairs["ratio"].median()
	norm = pairs.assign(brand=pairs["brand"].map(_normalize_str),
	                    line=pairs["line"].map(_normalize_str))
	ratio_by_brand = norm.groupby("brand")["ratio"].median().to_dict()
	ratio_by_brand_line = norm.groupby(["brand", "line"])["ratio"].median().to_dict()

	# Ridge on features to predict wholesale from retail + features
	X = encode_features(pairs)
	y = pairs["wholesale_aed"].values
	ridge = Ridge(alpha=1.0)
	ridge.fit(X, y)

	rf = RandomForestRegressor(n_estimators=100, random_state=42)
	rf.fit(X, y)

	# In-sample blended predictions -> relative-error interval (IQR of errors).
	ratio_pred = pairs.apply(
		lambda r: _pick_ratio(_normalize_str(r["brand"]), _normalize_str(r["line"]),
		                      ratio_by_brand_line, ratio_by_brand,
		                      float(ratio_global) if pd.notna(ratio_global) else 0.5),
		axis=1,
	).values * pairs["retail_aed"].astype(float).values
	blended = 0.4 * ratio_pred + 0.3 * ridge.predict(X) + 0.3 * rf.predict(X)
	rel_err = (y - blended) / blended
	if len(pairs) >= 5:
		interval = (float(np.quantile(rel_err, 0.25)), float(np.quantile(rel_err, 0.75)))
		interval_basis = "iqr"
	else:
		interval = (-0.15, 0.15)
		interval_basis = "default"

	return {
		"ratio_global": float(ratio_global) if pd.notna(ratio_global) else 0.5,
		"ratio_by_brand": ratio_by_brand,
		"ratio_by_brand_line": ratio_by_brand_line,
		"ridge": ridge,
		"rf": rf,
		"feature_columns": list(X.columns),
		"interval": interval,
		"interval_basis": interval_basis,
	}


def predict_for_retail(retail_df: pd.DataFrame, models: dict, known_wholesale_keys: set) -> pd.DataFrame:
	ret = retail_df.copy()
	ret["_key"] = _key(ret)
	# Filter to those without known wholesale
	ret = ret[~ret["_key"].isin(known_wholesale_keys)].copy()

	# If nothing to predict, return empty with expected columns
	if ret.empty:
		cols = [
			"brand", "line", "name", "size_ml", "concentration",
			"retail_aed", "predicted_wholesale_aed", "ci_low", "ci_high",
			"confidence_label", "estimator"
		]
		return pd.DataFrame(columns=cols)

	# Prepare ratio guesses
	def pick_ratio(row):
		brand = _normalize_str(row["brand"])
		line = _normalize_str(row["line"])
		return _pick_ratio(brand, line, models["ratio_by_brand_line"],
		                   models["ratio_by_brand"], models["ratio_global"])

	ret["ratio"] = ret.apply(pick_ratio, axis=1)
	ret["ratio_pred"] = ret["retail_aed"].astype(float) * ret["ratio"].astype(float)

	# Ridge predictions
	Xr = encode_features(ret)
	# add missing columns
	for c in models["feature_columns"]:
		if c not in Xr.columns:
			Xr[c] = 0
	Xr = Xr[models["feature_columns"]]
	ridge_pred = models["ridge"].predict(Xr) if len(Xr) > 0 else np.array([])
	ret["ridge_pred"] = ridge_pred

	rf_pred = models["rf"].predict(Xr) if len(Xr) > 0 else np.array([])
	ret["rf_pred"] = rf_pred

	# Blend: ratio 40%, Ridge 30%, RF 30%
	ret["predicted_wholesale_aed"] = (
		0.4 * ret["ratio_pred"]
		+ 0.3 * ret["ridge_pred"]
		+ 0.3 * ret["rf_pred"]
	)

	# Prediction interval from training-error IQR (falls back to ±15% when <5 pairs).
	lo, hi = models["interval"]
	ret["ci_low"] = ret["predicted_wholesale_aed"] * (1 + lo)
	ret["ci_high"] = ret["predicted_wholesale_aed"] * (1 + hi)

	# Confidence: based on whether brand-line ratio existed and retail available
	def conf_label(row):
		brand = _normalize_str(row["brand"])
		line = _normalize_str(row["line"])
		if (brand, line) in models["ratio_by_brand_line"]:
			return "High"
		if brand in models["ratio_by_brand"]:
			return "Med"
		return "Low"

	ret["confidence_label"] = ret.apply(conf_label, axis=1)
	ret["estimator"] = np.where(ret["confidence_label"] == "High", "ratio", "blend")

	return ret[[
		"brand", "line", "name", "size_ml", "concentration",
		"retail_aed", "predicted_wholesale_aed", "ci_low", "ci_high",
		"confidence_label", "estimator"
	]]


def evaluate_model(pairs: pd.DataFrame) -> None:
	"""Precision/recall at the 20%+ spread threshold on an 80/20 hold-out split.

	'20%+ spread' = wholesale_aed / retail_aed <= 0.80. All numbers printed are
	computed from the provided pairs; small samples make them noisy.
	"""
	if len(pairs) < 5:
		print(f"WARNING: {len(pairs)} pairs — too few for a reliable split (need 5+).")
		return

	from sklearn.model_selection import train_test_split

	train_pairs, test_pairs = train_test_split(pairs, test_size=0.2, random_state=42)
	models = train_models(train_pairs)

	test_retail = test_pairs[
		["brand", "line", "name", "size_ml", "concentration", "retail_aed"]
	].copy()
	pred_df = predict_for_retail(test_retail, models, known_wholesale_keys=set())

	if pred_df.empty:
		print("No predictions generated for test split.")
		return

	merged = pd.merge(
		test_pairs[[
			"brand", "line", "name", "size_ml", "concentration",
			"wholesale_aed", "retail_aed",
		]],
		pred_df[[
			"brand", "line", "name", "size_ml", "concentration",
			"predicted_wholesale_aed",
		]],
		on=["brand", "line", "name", "size_ml", "concentration"],
	)

	if merged.empty:
		print("Merge produced no rows — key mismatch between test and predictions.")
		return

	SPREAD_THRESHOLD = 0.80  # wholesale <= 80% of retail → >=20% spread
	merged["actual_flag"] = (
		merged["wholesale_aed"] / merged["retail_aed"] <= SPREAD_THRESHOLD
	)
	merged["predicted_flag"] = (
		merged["predicted_wholesale_aed"] / merged["retail_aed"] <= SPREAD_THRESHOLD
	)

	tp = int(((merged["predicted_flag"]) & (merged["actual_flag"])).sum())
	fp = int(((merged["predicted_flag"]) & (~merged["actual_flag"])).sum())
	precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")

	fn = int(((~merged["predicted_flag"]) & (merged["actual_flag"])).sum())
	recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")

	print(f"Evaluation (n_test={len(merged)}):")
	print(f"  Flagged spread >=20%: {int(merged['predicted_flag'].sum())}")
	print(f"  Precision: {precision:.1%}   Recall: {recall:.1%}")
	print("  Caveat: computed on the shipped sample dataset; treat as a code check,")
	print("  not a performance claim — the metric is noisy at this sample size.")


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--train", required=True)
	parser.add_argument("--retail", required=True)
	parser.add_argument("--out", required=True)
	parser.add_argument("--evaluate", action="store_true",
	                    help="Run hold-out evaluation and print precision metric.")
	args = parser.parse_args()

	wholesale_df = pd.read_csv(args.train)
	retail_df = pd.read_csv(args.retail)

	pairs = prepare_training_pairs(wholesale_df, retail_df)

	if args.evaluate:
		evaluate_model(pairs)
		return
	if len(pairs) > 0:
		models = train_models(pairs)
	else:
		# Fallback minimal model
		models = {
			"ratio_global": 0.5,
			"ratio_by_brand": {},
			"ratio_by_brand_line": {},
			"ridge": Ridge().fit(np.zeros((1,1)), np.zeros(1)),
			"rf": RandomForestRegressor(n_estimators=10, random_state=42).fit(np.zeros((1,1)), np.zeros(1)),
			"feature_columns": ["size_ml"],
			"interval": (-0.15, 0.15),
			"interval_basis": "default",
		}

	known_keys = set(_key(wholesale_df))
	pred = predict_for_retail(retail_df, models, known_keys)
	pred.to_csv(args.out, index=False)
	print(f"Wrote predictions to {args.out} (rows: {len(pred)})")

if __name__ == "__main__":
	main()
