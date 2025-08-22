import argparse
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge

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
		df[["brand", "line", "concentration"]].applymap(lambda s: str(s).strip().lower())
	)
	X["size_ml"] = df["size_ml"].astype(float).fillna(0)
	return X


def train_models(pairs: pd.DataFrame):
	# Ratio estimator (brand- and brand-line-level medians)
	ratio_global = pairs["ratio"].median()
	ratio_by_brand = pairs.groupby("brand")["ratio"].median().to_dict()
	ratio_by_brand_line = pairs.groupby(["brand", "line"])["ratio"].median().to_dict()

	# Ridge on features to predict wholesale from retail + features
	X = encode_features(pairs)
	y = pairs["wholesale_aed"].values
	ridge = Ridge(alpha=1.0)
	ridge.fit(X, y)

	return {
		"ratio_global": float(ratio_global) if pd.notna(ratio_global) else 0.5,
		"ratio_by_brand": ratio_by_brand,
		"ratio_by_brand_line": ratio_by_brand_line,
		"ridge": ridge,
		"feature_columns": list(X.columns),
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
		cand = models["ratio_by_brand_line"].get((brand, line))
		if cand is None:
			cand = models["ratio_by_brand"].get(brand)
		if cand is None:
			cand = models["ratio_global"]
		return float(cand)

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

	# Blend
	ret["predicted_wholesale_aed"] = 0.5 * ret["ratio_pred"] + 0.5 * ret["ridge_pred"]

	# Simple CI using IQR of ratio errors if available
	ci_width = 0.15  # 15% band default
	ret["ci_low"] = ret["predicted_wholesale_aed"] * (1 - ci_width)
	ret["ci_high"] = ret["predicted_wholesale_aed"] * (1 + ci_width)

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


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--train", required=True)
	parser.add_argument("--retail", required=True)
	parser.add_argument("--out", required=True)
	args = parser.parse_args()

	wholesale_df = pd.read_csv(args.train)
	retail_df = pd.read_csv(args.retail)

	pairs = prepare_training_pairs(wholesale_df, retail_df)
	if len(pairs) > 0:
		models = train_models(pairs)
	else:
		# Fallback minimal model
		models = {
			"ratio_global": 0.5,
			"ratio_by_brand": {},
			"ratio_by_brand_line": {},
			"ridge": Ridge().fit(np.zeros((1,1)), np.zeros(1)),
			"feature_columns": ["size_ml"],
		}

	known_keys = set(_key(wholesale_df))
	pred = predict_for_retail(retail_df, models, known_keys)
	pred.to_csv(args.out, index=False)
	print(f"Wrote predictions to {args.out} (rows: {len(pred)})")

if __name__ == "__main__":
	main()
