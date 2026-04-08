const { NseIndia } = require("stock-nse-india");
const fs = require("fs");
const path = require("path");

async function fetchSymbols() {
    try {
        const nseIndia = new NseIndia();
        const symbols = await nseIndia.getAllStockSymbols();
        
        // Filter out non-alphanumeric or index names if any, but the API usually returns pure symbols
        const cleanSymbols = symbols.filter(s => s && typeof s === 'string' && !s.includes('NIFTY'));
        
        const outPath = path.join(__dirname, "scan_results", "nse_symbols.json");
        fs.writeFileSync(outPath, JSON.stringify(cleanSymbols, null, 2), "utf-8");
        
        console.log(`Successfully fetched ${cleanSymbols.length} official symbols from NSE.`);
    } catch (error) {
        console.error("Error fetching symbols:", error.message);
        process.exit(1);
    }
}

fetchSymbols();
