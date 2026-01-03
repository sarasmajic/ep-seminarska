import React, { useState } from 'react';
import { Upload, TrendingDown, TrendingUp, AlertCircle, FileSpreadsheet, Package, Box } from 'lucide-react';
import * as XLSX from 'xlsx';

const PriceComparisonApp = () => {
  const [sparData, setSparData] = useState(null);
  const [mercatorData, setMercatorData] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const standardizeName = (name) => {
    if (!name) return "";
    
    let nameStr = String(name).toUpperCase();
    nameStr = nameStr.replace(/<[^>]+>/g, ' ');
    nameStr = nameStr.replace(/\s*\n\s*/g, ' ');
    nameStr = nameStr.replace(/\s+/g, ' ');
    nameStr = nameStr.trim();
    
    // Fix volume notation FIRST
    nameStr = nameStr.replace(/(\d+)\s*,\s*(\d+)/g, '$1.$2');
    nameStr = nameStr.replace(/(\d+[\d.]*)\s+(ML|L|CL|DL)\b/g, '$1$2');
    nameStr = nameStr.replace(/(\d+)\s*X\s+(\d+[\d.]*)/g, '$1X$2');
    
    const unwantedPatterns = [
      /V KOŠARICO/g,
      /NAKUP PAKETA.*IZDELKOV/g,
      /PONUDBA VELJA DO:.*/g,
      /PC\d+:\d+,\d+€/g,
      /\d+,\d+\s*€\/\s*\d+[A-Z]+/g,
      /\s*-\s*\d+%/g,
      /^\d+\.\s*/g,
    ];
    
    unwantedPatterns.forEach(pattern => {
      nameStr = nameStr.replace(pattern, '');
    });
    
    nameStr = nameStr.replace(/[^\w\s,.X()\-]/g, ' ');
    nameStr = nameStr.replace(/\s+/g, ' ');
    nameStr = nameStr.replace(/\s*\.\s*/g, '.');
    nameStr = nameStr.replace(/\s*\(\s*/g, ' (');
    nameStr = nameStr.replace(/\s*\)\s*/g, ') ');
    nameStr = nameStr.replace(/\s*-\s*/g, '-');
    nameStr = nameStr.replace(/^[,\s\.]+|[,\s\.]+$/g, '');
    
    return nameStr.trim();
  };

  const cleanPrice = (priceValue) => {
    if (!priceValue) return null;
    
    let priceStr = String(priceValue).replace(/[^\d,\.]/g, '');
    
    if (priceStr.includes(',') && priceStr.includes('.')) {
      priceStr = priceStr.replace(/\./g, '').replace(',', '.');
    } else if (priceStr.includes(',')) {
      priceStr = priceStr.replace(',', '.');
    }
    
    const price = parseFloat(priceStr);
    return isNaN(price) ? null : price;
  };

  const extractVolume = (name) => {
    const nameUpper = name.toUpperCase();
    
    // Check for PACKAGE notation
    const packageMatch = nameUpper.match(/(\d+)X(\d*\.?\d+)(ML|L|CL|DL)\b/);
    if (packageMatch) {
      const count = parseInt(packageMatch[1]);
      const volumeNum = parseFloat(packageMatch[2]);
      const unit = packageMatch[3];
      
      let volumeMl = volumeNum;
      if (unit === 'L') volumeMl = volumeNum * 1000;
      else if (unit === 'CL') volumeMl = volumeNum * 10;
      else if (unit === 'DL') volumeMl = volumeNum * 100;
      
      volumeMl = Math.round(volumeMl);
      const totalMl = volumeMl * count;
      const volumeStr = `PACK_${count}X${volumeMl}ML`;
      
      return { str: volumeStr, ml: totalMl, isPackage: true, count, singleUnitMl: volumeMl };
    }
    
    // Check for SINGLE ITEM volume
    const volumeMatch = nameUpper.match(/(?<![\dX])(\d*\.?\d+)(ML|L|CL|DL)\b/);
    if (volumeMatch) {
      const volumeNum = parseFloat(volumeMatch[1]);
      const unit = volumeMatch[2];
      
      let volumeMl = volumeNum;
      if (unit === 'L') volumeMl = volumeNum * 1000;
      else if (unit === 'CL') volumeMl = volumeNum * 10;
      else if (unit === 'DL') volumeMl = volumeNum * 100;
      
      volumeMl = Math.round(volumeMl);
      const volumeStr = `SINGLE_${volumeMl}ML`;
      
      return { str: volumeStr, ml: volumeMl, isPackage: false, count: 1, singleUnitMl: volumeMl };
    }
    
    return { str: null, ml: null, isPackage: false, count: null, singleUnitMl: null };
  };

  const extractFlavor = (name) => {
    const nameUpper = name.toUpperCase();
    
    const flavorKeywords = [
      'CITRUS', 'LIMONA', 'POMARANČA', 'POMARANCA', 'ORANGE',
      'BOROVNICA', 'BLUEBERRY', 'BRUSNICA', 'JAGODA', 'STRAWBERRY',
      'MALINA', 'RASPBERRY', 'LUBENICA', 'WATERMELON', 'ANANAS', 'PINEAPPLE',
      'MANGO', 'MENTOL', 'META', 'MINT', 'GRENIVKA', 'GRAPEFRUIT',
      'VANILIJA', 'VANILLA', 'KOKOS', 'COCONUT', 'MEŠANO SADJE', 'MULTIFRUIT',
      'FRUITY', 'TUTTI FRUTTI', 'TROPSKO SADJE', 'TROPICAL', 'CLASSIC', 'ORIGINAL',
      'ZERO', 'SUGAR FREE', 'SUGARFREE', 'BREZ SLADKORJA', 'SUMMER EDITION',
      'WINTER', 'WINTER EDITION', 'ULTRA', 'PIPELINE PUNCH', 'RIO PUNCH',
      'GREEN APPLE', 'ZELENO JABOLKO', 'BLACK CHERRY', 'ČRNA ČEŠNJA',
      'GOJI BERRY', 'STRONG FOCUS', 'STIMULATION', 'MOUNTAIN BLAST',
      'JABOLKO', 'APPLE', 'LIMETA', 'LIME', 'HROŠKA', 'PEAR', 'MARELICA',
      'APRICOT', 'BEZEG', 'ELDERBERRY', 'INGVER', 'GINGER', 'KIWI',
      'BANANA', 'PASSIONFRUIT', 'PASIJONKA', 'COLA', 'TEA', 'ČAJ',
      'MATCHA', 'BRESKEV', 'PEACH', 'YUZU', 'YERBA MATE', 'MATE',
      'ICE TEA', 'LEDENI ČAJ', 'LEMON', 'PEPSI', 'COCA COLA', 'COCA-COLA',
      'COLA ZERO', 'COCA COLA ZERO', 'SPRITE', 'FANTA', 'FANTA ORANGE',
      'MIRINDA', '7UP', 'SCHWEPPES', 'TANGERINA', 'TANGERINE', 'MANDARINA'
    ];
    
    const flavors = [];
    flavorKeywords.forEach(flavor => {
      if (flavor.includes(' ')) {
        if (nameUpper.includes(flavor)) {
          flavors.push(flavor.replace(/\s+/g, '_'));
        }
      } else {
        const pattern = new RegExp('\\b' + flavor + '\\b');
        if (pattern.test(nameUpper)) {
          flavors.push(flavor);
        }
      }
    });
    
    return [...new Set(flavors)].sort();
  };

  const extractBrand = (name) => {
    const nameUpper = name.toUpperCase();
    const brands = [
      'RED BULL', 'MONSTER', 'HELL', 'SHARK', 'POWERADE', 'OSHEE', 'ISOSTAR',
      'S BUDGET', 'S-BUDGET', 'CLUB MATE', 'CLUB-MATE', 'PERFECT TED',
      'FRUCTAL', 'NUTREND', 'NOCCO', '4MOVE', 'DANA', 'GATORADE', 'RAUCH',
      'BURN', 'BOOSTER', 'MTV UP', 'SQUID GAME', 'VITAMIN WELL',
      'FUNCTIONALL', 'ZALA', 'BRITE', 'HIDRA UP', 'PRIME HYDRATION',
      'LOHILO', 'VITALITY', 'ACTIVEFIT', 'SPAR', 'SOLA', 'ROSSI',
      'PEPSI', 'COCA COLA', 'COCA-COLA', 'COCA', 'SPRITE', 'FANTA',
      'MIRINDA', 'SCHWEPPES', 'TANGERINA', 'TANGERINE', 'MANDARINA'
    ];
    
    const sortedBrands = brands.sort((a, b) => b.length - a.length);
    
    for (const brand of sortedBrands) {
      if (nameUpper.includes(brand)) {
        if (brand === 'S-BUDGET') return 'S_BUDGET';
        if (brand === 'CLUB-MATE') return 'CLUB_MATE';
        if (brand === 'COCA-COLA') return 'COCA_COLA';
        return brand.replace(/\s+/g, '_');
      }
    }
    return 'NOBRAND';
  };

  const createMatchKey = (name) => {
    const brand = extractBrand(name);
    const flavor = extractFlavor(name);
    const volume = extractVolume(name);
    
    const volumeKey = volume.str || 'NOVOLUME';
    const flavorKey = flavor.length > 0 ? flavor.slice(0, 3).join('_') : 'NOFLAVOR';
    
    return `${brand}_${flavorKey}_${volumeKey}`;
  };

  const handleFileUpload = async (file, type) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target.result);
          const workbook = XLSX.read(data, { type: 'array' });
          const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
          const jsonData = XLSX.utils.sheet_to_json(firstSheet);
          
          const products = [];
          jsonData.forEach(row => {
            const name = standardizeName(type === 'spar' ? row.name_0 : row.name);
            const price = cleanPrice(type === 'spar' ? row.price_0 : row.price3);
            
            if (name && price !== null) {
              const brand = extractBrand(name);
              const flavor = extractFlavor(name);
              const volume = extractVolume(name);
              const matchKey = createMatchKey(name);
              
              products.push({
                name,
                price,
                brand,
                flavor,
                volumeStr: volume.str,
                volumeMl: volume.ml,
                isPackage: volume.isPackage,
                packageCount: volume.count,
                singleUnitMl: volume.singleUnitMl,
                matchKey
              });
            }
          });
          
          resolve(products);
        } catch (err) {
          reject(err);
        }
      };
      
      reader.onerror = reject;
      reader.readAsArrayBuffer(file);
    });
  };

  const handleSparFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setError(null);
    try {
      const products = await handleFileUpload(file, 'spar');
      setSparData({ filename: file.name, products });
    } catch (err) {
      setError('Napaka pri branju Spar datoteke: ' + err.message);
    }
  };

  const handleMercatorFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setError(null);
    try {
      const products = await handleFileUpload(file, 'mercator');
      setMercatorData({ filename: file.name, products });
    } catch (err) {
      setError('Napaka pri branju Mercator datoteke: ' + err.message);
    }
  };

  const handleCompare = () => {
    if (!sparData || !mercatorData) {
      setError('Prosim naložite obe datoteki');
      return;
    }

    setLoading(true);
    setError(null);

    setTimeout(() => {
      try {
        const sparByKey = {};
        sparData.products.forEach(p => {
          if (!sparByKey[p.matchKey]) sparByKey[p.matchKey] = [];
          sparByKey[p.matchKey].push(p);
        });

        const mercatorByKey = {};
        mercatorData.products.forEach(p => {
          if (!mercatorByKey[p.matchKey]) mercatorByKey[p.matchKey] = [];
          mercatorByKey[p.matchKey].push(p);
        });

        const matches = [];
        Object.keys(sparByKey).forEach(key => {
          if (mercatorByKey[key]) {
            sparByKey[key].forEach(sp => {
              mercatorByKey[key].forEach(mp => {
                if (sp.brand === mp.brand && 
                    JSON.stringify(sp.flavor) === JSON.stringify(mp.flavor) &&
                    sp.volumeMl === mp.volumeMl && 
                    sp.isPackage === mp.isPackage) {
                  
                  const diff = sp.price - mp.price;
                  if (Math.abs(diff) > 0.01) {
                    matches.push({
                      brand: sp.brand,
                      flavor: sp.flavor.join(', ') || 'N/A',
                      volume: sp.volumeStr,
                      volumeMl: sp.volumeMl,
                      isPackage: sp.isPackage,
                      packageCount: sp.packageCount,
                      sparName: sp.name,
                      sparPrice: sp.price,
                      mercatorName: mp.name,
                      mercatorPrice: mp.price,
                      difference: diff,
                      percentDiff: (diff / mp.price) * 100
                    });
                  }
                }
              });
            });
          }
        });

        matches.sort((a, b) => Math.abs(b.percentDiff) - Math.abs(a.percentDiff));

        // Calculate statistics
        const sparPackages = sparData.products.filter(p => p.isPackage).length;
        const sparSingles = sparData.products.filter(p => !p.isPackage && p.volumeStr).length;
        const mercatorPackages = mercatorData.products.filter(p => p.isPackage).length;
        const mercatorSingles = mercatorData.products.filter(p => !p.isPackage && p.volumeStr).length;

        setResults({
          matches,
          totalSpar: sparData.products.length,
          totalMercator: mercatorData.products.length,
          sparPackages,
          sparSingles,
          mercatorPackages,
          mercatorSingles
        });
      } catch (err) {
        setError('Napaka pri primerjavi: ' + err.message);
      } finally {
        setLoading(false);
      }
    }, 100);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8 mb-6">
          <h1 className="text-4xl font-bold text-gray-800 mb-2 text-center">
            Primerjava Cen
          </h1>
          <p className="text-center text-gray-600 mb-2">Spar vs Mercator</p>
          <div className="flex items-center justify-center gap-2 text-sm text-gray-500 mb-6">
            <FileSpreadsheet className="w-4 h-4" />
            <span>Excel datoteke (.xlsx, .xls) • Razlikuje pakete od posameznih izdelkov</span>
          </div>

          <div className="grid md:grid-cols-2 gap-6 mb-6">
            <div className="border-2 border-dashed border-green-300 rounded-lg p-6 hover:border-green-500 transition">
              <label className="flex flex-col items-center cursor-pointer">
                <Upload className="w-12 h-12 text-green-600 mb-3" />
                <span className="text-lg font-semibold text-gray-700 mb-2">Spar Excel</span>
                <span className="text-sm text-gray-500 mb-3 text-center">
                  {sparData ? `✓ ${sparData.filename} (${sparData.products.length} izdelkov)` : 'Kliknite za nalaganje'}
                </span>
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleSparFile}
                  className="hidden"
                />
              </label>
            </div>

            <div className="border-2 border-dashed border-red-300 rounded-lg p-6 hover:border-red-500 transition">
              <label className="flex flex-col items-center cursor-pointer">
                <Upload className="w-12 h-12 text-red-600 mb-3" />
                <span className="text-lg font-semibold text-gray-700 mb-2">Mercator Excel</span>
                <span className="text-sm text-gray-500 mb-3 text-center">
                  {mercatorData ? `✓ ${mercatorData.filename} (${mercatorData.products.length} izdelkov)` : 'Kliknite za nalaganje'}
                </span>
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleMercatorFile}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          <button
            onClick={handleCompare}
            disabled={!sparData || !mercatorData || loading}
            className="w-full bg-indigo-600 text-white py-4 rounded-lg font-semibold text-lg hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
          >
            {loading ? 'Obdelavam...' : 'Primerjaj Cene'}
          </button>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
              <AlertCircle className="text-red-500" />
              <span className="text-red-700">{error}</span>
            </div>
          )}
        </div>

        {results && (
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">Rezultati</h2>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="bg-green-50 p-4 rounded-lg border-2 border-green-200">
                  <div className="text-3xl font-bold text-green-700">{results.totalSpar}</div>
                  <div className="text-sm text-gray-600">Spar izdelkov</div>
                </div>
                <div className="bg-red-50 p-4 rounded-lg border-2 border-red-200">
                  <div className="text-3xl font-bold text-red-700">{results.totalMercator}</div>
                  <div className="text-sm text-gray-600">Mercator izdelkov</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg border-2 border-purple-200">
                  <div className="text-3xl font-bold text-purple-700">{results.matches.length}</div>
                  <div className="text-sm text-gray-600">Razlike v cenah</div>
                </div>
                <div className="bg-orange-50 p-4 rounded-lg border-2 border-orange-200">
                  <div className="text-3xl font-bold text-orange-700">
                    {results.sparPackages}/{results.mercatorPackages}
                  </div>
                  <div className="text-sm text-gray-600">Paketi (S/M)</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-green-50 p-3 rounded-lg flex items-center gap-2 border border-green-200">
                  <Package className="w-5 h-5 text-green-700" />
                  <div className="text-sm">
                    <span className="font-semibold text-green-800">Spar:</span> {results.sparPackages} paketov, {results.sparSingles} posameznih
                  </div>
                </div>
                <div className="bg-red-50 p-3 rounded-lg flex items-center gap-2 border border-red-200">
                  <Package className="w-5 h-5 text-red-700" />
                  <div className="text-sm">
                    <span className="font-semibold text-red-800">Mercator:</span> {results.mercatorPackages} paketov, {results.mercatorSingles} posameznih
                  </div>
                </div>
              </div>
            </div>

            {results.matches.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                Ni najdenih ujemajočih izdelkov z različnimi cenami
              </div>
            ) : (
              <div className="space-y-4">
                {results.matches.map((match, idx) => (
                  <div key={idx} className="border-2 border-gray-200 rounded-lg p-6 hover:shadow-lg transition">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        {match.isPackage ? (
                          <Package className="w-6 h-6 text-indigo-600" />
                        ) : (
                          <Box className="w-6 h-6 text-indigo-600" />
                        )}
                        <div>
                          <h3 className="text-xl font-bold text-gray-800">{match.brand}</h3>
                          <p className="text-gray-600">{match.flavor}</p>
                          <p className="text-sm text-gray-500">
                            {match.isPackage ? `Paket ${match.packageCount}x` : 'Posamezni'} • {match.volume}
                          </p>
                        </div>
                      </div>
                      <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
                        match.difference < 0 ? 'bg-green-100 text-green-700 border-2 border-green-300' : 'bg-red-100 text-red-700 border-2 border-red-300'
                      }`}>
                        {match.difference < 0 ? <TrendingDown /> : <TrendingUp />}
                        <span className="font-bold">
                          {Math.abs(match.percentDiff).toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="bg-green-50 p-4 rounded-lg border-2 border-green-200">
                        <div className="text-sm font-semibold text-green-800 mb-2">SPAR 🟢</div>
                        <div className="text-sm text-gray-700 mb-2 line-clamp-2">{match.sparName}</div>
                        <div className="text-2xl font-bold text-green-700">€{match.sparPrice.toFixed(2)}</div>
                      </div>

                      <div className="bg-red-50 p-4 rounded-lg border-2 border-red-200">
                        <div className="text-sm font-semibold text-red-800 mb-2">MERCATOR 🔴</div>
                        <div className="text-sm text-gray-700 mb-2 line-clamp-2">{match.mercatorName}</div>
                        <div className="text-2xl font-bold text-red-700">€{match.mercatorPrice.toFixed(2)}</div>
                      </div>
                    </div>

                    <div className="mt-4 text-center">
                      {match.difference < 0 ? (
                        <p className="text-green-800 font-semibold text-lg bg-green-100 py-2 rounded-lg border-2 border-green-300">
                          ⭐ Spar je cenejši za €{Math.abs(match.difference).toFixed(2)} ⭐
                        </p>
                      ) : (
                        <p className="text-red-800 font-semibold text-lg bg-red-100 py-2 rounded-lg border-2 border-red-300">
                          ⭐ Mercator je cenejši za €{Math.abs(match.difference).toFixed(2)} ⭐
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PriceComparisonApp;