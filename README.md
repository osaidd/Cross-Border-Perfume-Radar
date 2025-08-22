# Cross-Border Perfume Radar (UAE → SG)

A data-driven tool to identify profitable perfume SKUs for cross-border trade from UAE to Singapore, helping e-commerce sellers make informed import decisions.

## 🎯 Problem Statement

Finding perfume SKUs with the best UAE→SG profit margins while ensuring sufficient market demand is currently a manual, time-consuming process. This tool provides a repeatable, data-driven approach to identify viable import opportunities.

## ✨ Key Features

- **SKU Analysis**: Calculate Landed Unit Cost (LUC) with confidence scoring
- **Market Intelligence**: SG competitor pricing and demand analysis
- **Profit Gap Calculation**: UAE wholesale vs. SG retail price analysis
- **Viability Scoring**: 0-100 score with Import/Wait/Skip recommendations
- **CSV Export**: Top-performing SKUs for easy analysis
- **Deep Dive Pages**: Detailed SKU analysis and reorder suggestions

## 🏗️ Architecture

- **Frontend**: Modern web interface for SKU search and analysis
- **Backend**: Data processing and calculation engine
- **Data Sources**: 
  - SG competitor snapshots (Shopee/Lazada)
  - Dubai wholesale pricing
  - Public retail proxies (Noon/Amazon.ae)
  - Cost parameters (shipping, FX, GST, packaging)

## 🚀 Getting Started

*Development setup instructions coming soon...*

## 📊 Data Flow

1. **Input**: SG competitor data, Dubai prices, cost parameters
2. **Processing**: LUC calculation, profit gap analysis, demand scoring
3. **Output**: Ranked SKU recommendations with viability scores

## 📈 Success Metrics

- Quick SKU lookup with LUC breakdown
- Ranked table of 20-50 viable SKUs
- Configurable cost parameters for accurate calculations
- Confidence flags for price data reliability

## 🔒 Compliance

- No PII collection
- Respects robots.txt and Terms of Service
- Public pages only
- Low-rate sampling to avoid disruption

## 📅 Development Timeline

- **Week 1**: Foundations
- **Week 2**: SG module
- **Week 3**: Dubai & costs
- **Week 4**: Scoring + UI
- **Week 5**: Polish + documentation

## 📚 Documentation

- [Product Requirements Document](docs/PRD.md)
- Technical specifications (coming soon)
- User guide (coming soon)

---

*Built for Imperial Oud and small e-commerce sellers in Singapore*
