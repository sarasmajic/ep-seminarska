import pandas as pd
import re
from collections import defaultdict

def standardize_name(name):
    """Standardize product names to identical format"""
    if pd.isna(name):
        return ""
    
    name_str = str(name)
    
    # Convert to uppercase for consistency
    name_str = name_str.upper()
    
    # Remove all HTML tags, line breaks, and extra whitespace
    name_str = re.sub(r'<[^>]+>', ' ', name_str)
    name_str = re.sub(r'\s*\n\s*', ' ', name_str)
    name_str = re.sub(r'\s+', ' ', name_str)
    name_str = name_str.strip()
    
    # CRITICAL FIX: Standardize volume notation FIRST before anything else
    # Fix "0, 5L" -> "0.5L", "4X 0, 5 L" -> "4X0.5L"
    # Remove spaces around commas in numbers
    name_str = re.sub(r'(\d+)\s*,\s*(\d+)', r'\1.\2', name_str)
    # Remove spaces before units
    name_str = re.sub(r'(\d+[\d.]*)\s+(ML|L|CL|DL)\b', r'\1\2', name_str)
    # Fix spacing around X in package notation
    name_str = re.sub(r'(\d+)\s*X\s+(\d+[\d.]*)', r'\1X\2', name_str)
    
    # Remove unwanted text patterns
    unwanted_patterns = [
        r'V KOŠARICO',
        r'NAKUP PAKETA.*IZDELKOV',
        r'PONUDBA VELJA DO:.*',
        r'PC\d+:\d+,\d+€',
        r'\d+,\d+\s*€/\s*\d+[A-Z]+',
        r'\s*-\s*\d+%',
        r'^\d+\.\s*',
    ]
    
    for pattern in unwanted_patterns:
        name_str = re.sub(pattern, '', name_str)
    
    # Remove special characters but keep important ones
    name_str = re.sub(r'[^\w\s,.X()\-]', ' ', name_str)
    
    # Fix spacing
    name_str = re.sub(r'\s+', ' ', name_str)
    name_str = re.sub(r'\s*\.\s*', '.', name_str)
    name_str = re.sub(r'\s*\(\s*', ' (', name_str)
    name_str = re.sub(r'\s*\)\s*', ') ', name_str)
    name_str = re.sub(r'\s*-\s*', '-', name_str)
    
    # Remove trailing/leading commas and dots
    name_str = re.sub(r'^[,\s\.]+|[,\s\.]+$', '', name_str)
    
    return name_str.strip()

def clean_price(price_value):
    """Extract and clean price to float"""
    if pd.isna(price_value):
        return None
    
    price_str = str(price_value)
    price_str = re.sub(r'[^\d,\.]', '', price_str)
    
    if ',' in price_str and '.' in price_str:
        price_str = price_str.replace('.', '').replace(',', '.')
    elif ',' in price_str:
        price_str = price_str.replace(',', '.')
    
    try:
        return float(price_str)
    except ValueError:
        return None

def extract_and_standardize_volume(name):
    """
    Extract and standardize volume from name - IMPORTANT: differentiate packages from single items
    Returns: (volume_string, volume_ml, is_package, package_count, single_unit_ml)
    """
    name_upper = name.upper()
    
    # FIRST: Check for PACKAGE notation (e.g., 4X250ML, 6X0.33L, 4X0.5L)
    # More flexible regex that handles various formats
    package_match = re.search(r'(\d+)X(\d*\.?\d+)(ML|L|CL|DL)\b', name_upper)
    if package_match:
        count = int(package_match.group(1))
        volume_num = float(package_match.group(2))
        unit = package_match.group(3)
        
        # Convert to ML
        if unit == 'L':
            volume_ml = volume_num * 1000
        elif unit == 'CL':
            volume_ml = volume_num * 10
        elif unit == 'DL':
            volume_ml = volume_num * 100
        else:
            volume_ml = volume_num
        
        # Round to avoid floating point errors
        volume_ml = round(volume_ml)
        
        # This is a PACKAGE - store SINGLE unit volume
        volume_str = f"PACK_{count}X{int(volume_ml)}ML"
        
        # Total volume for the entire package
        total_ml = volume_ml * count
        
        return volume_str, total_ml, True, count, volume_ml
    
    # SECOND: Check for SINGLE ITEM volume (e.g., 250ML, 0.5L, 33CL, 500ML)
    # Match standalone volume (not preceded by number and X)
    volume_match = re.search(r'(?<![\dX])(\d*\.?\d+)(ML|L|CL|DL)\b', name_upper)
    if volume_match:
        volume_num = float(volume_match.group(1))
        unit = volume_match.group(2)
        
        # Convert to ML
        if unit == 'L':
            volume_ml = volume_num * 1000
        elif unit == 'CL':
            volume_ml = volume_num * 10
        elif unit == 'DL':
            volume_ml = volume_num * 100
        else:
            volume_ml = volume_num
        
        # Round to avoid floating point errors
        volume_ml = round(volume_ml)
        
        # This is a SINGLE ITEM
        volume_str = f"SINGLE_{int(volume_ml)}ML"
        
        return volume_str, volume_ml, False, 1, volume_ml
    
    return None, None, False, None, None

def extract_flavor(name):
    """Extract exact flavor from name without modification"""
    name_upper = name.upper()
    
    # POSEBNI PRIMERI ZA OSHEE - moramo natančno razlikovati
    # Oshee sadni mix in pomarančni nista isti okus!
    
    # Najprej preverimo specifične okuse za Oshee
    if 'OSHEE' in name_upper:
        # Preverimo specifične okuse Oshee
        if 'SADNI' in name_upper or 'SADNI MIX' in name_upper or 'FRUIT MIX' in name_upper:
            return ('SADNI_MIX',)
        elif 'POMARANČNI' in name_upper or 'POMARANCA' in name_upper or 'ORANGE' in name_upper:
            # BLOOD ORANGE je isto kot POMARANCA/RDEČA POMARANČA
            return ('POMARANCA',)
        elif 'LIMONA' in name_upper or 'LEMON' in name_upper:
            return ('LIMONA',)
        elif 'BRESKEV' in name_upper or 'PEACH' in name_upper:
            return ('BRESKEV',)
        elif 'MULTIVITAMIN' in name_upper:
            return ('MULTIVITAMIN',)
        elif 'BOROVNICA' in name_upper or 'BLUEBERRY' in name_upper:
            return ('BOROVNICA',)
    
    # POSEBNI PRIMER ZA CARIBBEAN - to je specifičen okus/izdelek
    if 'CARIBBEAN' in name_upper:
        return ('CARIBBEAN',)
    
    # Poseben primer: BLOOD ORANGE je isto kot RDEČA POMARANČA/POMARANCA
    # Standardiziramo vse pomarančne okuse na POMARANCA
    if 'BLOOD ORANGE' in name_upper or 'BLOODORANGE' in name_upper or 'RED ORANGE' in name_upper or 'RDEČA POMARANČA' in name_upper:
        return ('POMARANCA',)
    
    # Splošni seznam okusov - zdaj standardiziramo vse pomarančne variacije
    flavor_keywords = [
        'CITRUS', 'LIMONA', 'POMARANČA', 'POMARANCA', 'ORANGE',
        'BOROVNICA', 'BLUEBERRY', 'BRUSNICA',
        'JAGODA', 'STRAWBERRY',
        'MALINA', 'RASPBERRY',
        'LUBENICA', 'WATERMELON',
        'ANANAS', 'PINEAPPLE',
        'MANGO',
        'MENTOL', 'META', 'MINT',
        'GRENIVKA', 'GRAPEFRUIT',
        'VANILIJA', 'VANILLA',
        'KOKOS', 'COCONUT',
        'MEŠANO SADJE', 'MULTIFRUIT', 'FRUITY', 'TUTTI FRUTTI',
        'SADNI', 'FRUIT', 'MIXED FRUIT',
        'TROPSKO SADJE', 'TROPICAL',
        'CLASSIC', 'ORIGINAL',
        'ZERO', 'SUGAR FREE', 'SUGARFREE', 'BREZ SLADKORJA',
        'SUMMER EDITION', 'WINTER', 'WINTER EDITION',
        'ULTRA', 'PIPELINE PUNCH', 'RIO PUNCH',
        'GREEN APPLE', 'ZELENO JABOLKO',
        'BLACK CHERRY', 'ČRNA ČEŠNJA',
        'GOJI BERRY',
        'STRONG FOCUS', 'STIMULATION',
        'MOUNTAIN BLAST',
        'JABOLKO', 'APPLE',
        'LIMETA', 'LIME',
        'HROŠKA', 'PEAR',
        'MARELICA', 'APRICOT',
        'BEZEG', 'ELDERBERRY',
        'INGVER', 'GINGER',
        'KIWI',
        'BANANA',
        'PASSIONFRUIT', 'PASIJONKA',
        'COLA',
        'TEA', 'ČAJ',
        'MATCHA',
        'BRESKEV', 'PEACH',
        'YUZU',
        'YERBA MATE', 'MATE',
        'ICE TEA', 'LEDENI ČAJ', 'LEMON', 'PEPSI', 'COCA COLA', 'COCA-COLA',
        'COLA ZERO', 'COCA COLA ZERO', 'SPRITE', 'FANTA', 'FANTA ORANGE',
        'MIRINDA', '7UP', 'SCHWEPPES', 'TANGERINA', 'TANGERINE', 'MANDARINA',
        'MULTIVITAMIN', 'VITAMIN',
        # Dodani za izdelke Caribbean
        'ISLAND', 'ISLAND PUNCH', 'PUNCH',
        'GUAVA', 'PASSION', 'MARACUJA'
    ]
    
    # Poiščemo vse okuse, ki so v imenu
    flavors = []
    for flavor in flavor_keywords:
        # Za besede s presledkom (npr. "COCA COLA")
        if ' ' in flavor:
            if flavor in name_upper:
                flavors.append(flavor.replace(' ', '_'))
        # Za enobesedne okuse uporabi word boundary
        else:
            pattern = r'\b' + flavor + r'\b'
            if re.search(pattern, name_upper):
                flavors.append(flavor)
    
    # Standardiziramo vse pomarančne okuse na POMARANCA
    # To vključuje: ORANGE, POMARANČA, POMARANCA, BLOOD ORANGE, RED ORANGE, RDEČA POMARANČA
    pomaranca_variants = ['ORANGE', 'POMARANČA', 'POMARANCA']
    if any(variant in flavors for variant in pomaranca_variants) or 'BLOOD' in name_upper and 'ORANGE' in name_upper:
        # Odstranimo vse pomarančne variante
        flavors = [f for f in flavors if f not in pomaranca_variants]
        # Dodamo standardiziran okus
        if 'POMARANCA' not in flavors:
            flavors.append('POMARANCA')
    
    # Uredi in odstrani duplikate
    flavors = sorted(set(flavors))
    
    # Če imamo Oshee izdelek brez okusa, dodamo "CLASSIC"
    if 'OSHEE' in name_upper and not flavors:
        flavors.append('CLASSIC')
    
    # Če ni najden noben okus, poskusimo izluščiti iz imena
    if not flavors:
        # Poiščemo ključne besede v imenu, ki niso znamke
        words = re.findall(r'\b[A-Z][A-Z]+\b', name_upper)
        known_brands = [
            'RED BULL', 'MONSTER', 'HELL', 'SHARK', 'POWERADE', 'OSHEE', 'ISOSTAR',
            'S BUDGET', 'S-BUDGET', 'CLUB MATE', 'CLUB-MATE', 'PERFECT TED', 
            'FRUCTAL', 'NUTREND', 'NOCCO', '4MOVE', 'DANA', 'GATORADE', 'RAUCH',
            'BURN', 'BOOSTER', 'MTV UP', 'OK', 'SQUID GAME', 'VITAMIN WELL',
            'FUNCTIONALL', 'ZALA', 'BRITE', 'HIDRA UP', 'PRIME HYDRATION',
            'LOHILO', 'VITALITY', 'ACTIVEFIT', 'SPAR', 'SOLA', 'ROSSI',
            'PEPSI', 'COCA', 'COLA', 'SPRITE', 'FANTA', 'MIRINDA', 'SCHWEPPES',
            'CARIBBEAN'  # Caribbean je okus, ne znamka
        ]
        
        # Odstranimo znamke in tehnične besede
        filtered_words = []
        for word in words:
            is_brand = False
            for brand in known_brands:
                if word in brand or brand in name_upper:
                    is_brand = True
                    break
            
            # Tehnične besede, ki niso okusi
            technical_terms = ['ML', 'L', 'CL', 'DL', 'X', 'PACK', 'CAN', 'BOTTLE', 
                             'PET', 'GLASS', 'ENERGY', 'DRINK', 'WATER', 'JUICE',
                             'LIMITED', 'EDITION', 'SUGAR', 'FREE', 'ZERO', 'LIGHT',
                             'SPORT', 'ISOTONIC', 'REFRESHING', 'COOL', 'FRESH',
                             'BLOOD', 'RED']  # Dodali BLOOD in RED, ker nista okus
            
            if not is_brand and word not in technical_terms and len(word) > 2:
                filtered_words.append(word)
        
        if filtered_words:
            flavors = filtered_words[:3]  # Vzamemo največ 3 besede
    
    return tuple(flavors) if flavors else tuple()

def extract_brand(name):
    """Extract brand from name"""
    name_upper = name.upper()
    
    # Oshee mora biti vedno prepoznan kot znamka
    if 'OSHEE' in name_upper:
        return 'OSHEE'
    
    # Caribbean NI znamka, ampak okus/izdelek - ne vračamo Caribbean kot znamko
    # če je Caribbean v imenu, iščemo drugo znamko
    if 'CARIBBEAN' in name_upper:
        # Poglejmo če je kakšna druga znamka v imenu
        other_brands = [
            'RED BULL', 'MONSTER', 'HELL', 'SHARK', 'POWERADE', 'ISOSTAR',
            'S BUDGET', 'S-BUDGET', 'CLUB MATE', 'CLUB-MATE', 'PERFECT TED', 
            'FRUCTAL', 'NUTREND', 'NOCCO', '4MOVE', 'DANA', 'GATORADE', 'RAUCH',
            'BURN', 'BOOSTER', 'MTV UP', 'OK', 'SQUID GAME', 'VITAMIN WELL',
            'FUNCTIONALL', 'ZALA', 'BRITE', 'HIDRA UP', 'PRIME HYDRATION',
            'LOHILO', 'VITALITY', 'ACTIVEFIT', 'SPAR', 'SOLA', 'ROSSI',
            'PEPSI', 'COCA COLA', 'COCA-COLA', 'COCA', 'SPRITE', 'FANTA', 'MIRINDA',
            'SCHWEPPES'
        ]
        
        for brand in other_brands:
            if brand in name_upper:
                if brand == 'S-BUDGET':
                    return 'S_BUDGET'
                elif brand == 'CLUB-MATE':
                    return 'CLUB_MATE'
                elif brand == 'COCA-COLA':
                    return 'COCA_COLA'
                else:
                    return brand.replace(' ', '_')
        # Če ni druge znamke, Caribbean je verjetno okus neke druge znamke
        return 'NOBRAND'
    
    brands = [
        'RED BULL', 'MONSTER', 'HELL', 'SHARK', 'POWERADE', 'ISOSTAR',
        'S BUDGET', 'S-BUDGET', 'CLUB MATE', 'CLUB-MATE', 'PERFECT TED', 
        'FRUCTAL', 'NUTREND', 'NOCCO', '4MOVE', 'DANA', 'GATORADE', 'RAUCH',
        'BURN', 'BOOSTER', 'MTV UP', 'OK', 'SQUID GAME', 'VITAMIN WELL',
        'FUNCTIONALL', 'ZALA', 'BRITE', 'HIDRA UP', 'PRIME HYDRATION',
        'LOHILO', 'VITALITY', 'ACTIVEFIT', 'SPAR', 'SOLA', 'ROSSI',
        'PEPSI', 'COCA COLA', 'COCA-COLA', 'COCA', 'SPRITE', 'FANTA', 'MIRINDA',
        'SCHWEPPES', 'TANGERINA', 'TANGERINE', 'MANDARINA'
    ]
    
    # Najprej preverimo dolge imena znamk
    for brand in sorted(brands, key=lambda x: len(x), reverse=True):
        if brand in name_upper:
            if brand == 'S-BUDGET':
                return 'S_BUDGET'
            elif brand == 'CLUB-MATE':
                return 'CLUB_MATE'
            elif brand == 'COCA-COLA':
                return 'COCA_COLA'
            else:
                return brand.replace(' ', '_')
    
    return 'NOBRAND'

def create_match_key(name):
    """
    Create a unique key for matching based on brand, flavor, and volume
    CRITICALLY: This now differentiates packages from single items
    """
    brand = extract_brand(name)
    flavor = extract_flavor(name)
    volume_str, volume_ml, is_package, package_count, single_unit_ml = extract_and_standardize_volume(name)
    
    # Use the full volume_str which includes PACK_ or SINGLE_ prefix
    if volume_str:
        volume_key = volume_str
    else:
        volume_key = "NOVOLUME"
    
    # Create flavor key - zdaj je BOLJ POMEMBEN za ujemanje
    if flavor:
        # Za Oshee izdelke moramo natančno razlikovati okuse
        if brand == 'OSHEE':
            flavor_key = "_".join(flavor)
        else:
            # Uporabimo samo prve 3 okuse, da preprečimo prevelike ključe
            flavor_key = "_".join(flavor[:3])
    else:
        flavor_key = "NOFLAVOR"
    
    # The match key now includes the PACK_ or SINGLE_ distinction
    return f"{brand}_{flavor_key}_{volume_key}"

# ========== MAIN PROCESSING ==========
print("Reading and preparing data...")
try:
    spar_df = pd.read_excel('spar.xlsx')
    mercator_df = pd.read_excel('mercator.xlsx')
except FileNotFoundError as e:
    print(f"Napaka pri branju datotek: {e}")
    print("Preveri, da sta datoteki 'spar.xlsx' in 'mercator.xlsx' v isti mapi.")
    exit()

print(f"Original Spar rows: {len(spar_df)}")
print(f"Original Mercator rows: {len(mercator_df)}")

# Prepare products
spar_products = []
print("\nProcessing Spar products...")
for idx, row in spar_df.iterrows():
    name = standardize_name(row.get('name_0', ''))
    price = clean_price(row.get('price_0', ''))
    
    if name and price is not None:
        brand = extract_brand(name)
        flavor = extract_flavor(name)
        volume_str, volume_ml, is_package, package_count, single_unit_ml = extract_and_standardize_volume(name)
        match_key = create_match_key(name)
        
        spar_products.append({
            'original_name': str(row.get('name_0', '')),
            'name': name,
            'price': price,
            'brand': brand,
            'flavor': flavor,
            'volume_str': volume_str,
            'volume_ml': volume_ml,
            'is_package': is_package,
            'package_count': package_count,
            'single_unit_ml': single_unit_ml,
            'match_key': match_key,
            'source': 'Spar'
        })

mercator_products = []
print("Processing Mercator products...")
for idx, row in mercator_df.iterrows():
    name = standardize_name(row.get('name', ''))
    price = clean_price(row.get('price3', ''))
    
    if name and price is not None:
        brand = extract_brand(name)
        flavor = extract_flavor(name)
        volume_str, volume_ml, is_package, package_count, single_unit_ml = extract_and_standardize_volume(name)
        match_key = create_match_key(name)
        
        mercator_products.append({
            'original_name': str(row.get('name', '')),
            'name': name,
            'price': price,
            'brand': brand,
            'flavor': flavor,
            'volume_str': volume_str,
            'volume_ml': volume_ml,
            'is_package': is_package,
            'package_count': package_count,
            'single_unit_ml': single_unit_ml,
            'match_key': match_key,
            'source': 'Mercator'
        })

print(f"\nProcessed Spar products: {len(spar_products)}")
print(f"Processed Mercator products: {len(mercator_products)}")

# Show some examples of how products are categorized
print("\n" + "="*80)
print("PRIMERI KATEGORIZACIJE IZDELKOV (Posebna pozornost na BLOOD ORANGE):")
print("="*80)

# Prikažemo posebej Blood Orange izdelke
blood_orange_products = [p for p in spar_products + mercator_products 
                         if 'BLOOD' in p['name'].upper() and 'ORANGE' in p['name'].upper()]

if blood_orange_products:
    print(f"\nNajdenih {len(blood_orange_products)} BLOOD ORANGE izdelkov (standardizirani kot POMARANCA):")
    for i, product in enumerate(blood_orange_products[:10]):
        package_type = "PAKET" if product['is_package'] else "POSAMEZNI"
        flavors = ', '.join(product['flavor']) if product['flavor'] else 'Brez okusa'
        print(f"{i+1}. {package_type}: {product['brand']} - {flavors}")
        print(f"   Ime: {product['name'][:70]}...")
        print(f"   Volume: {product['volume_str']}, Match key: {product['match_key']}")
        print()

# Pokažemo tudi standardne pomarančne izdelke za primerjavo
orange_products = [p for p in spar_products + mercator_products 
                   if 'POMARANCA' in p['flavor'] and p not in blood_orange_products]

if orange_products:
    print(f"\nNajdenih {len(orange_products)} drugih POMARANČNIH izdelkov:")
    for i, product in enumerate(orange_products[:5]):
        package_type = "PAKET" if product['is_package'] else "POSAMEZNI"
        flavors = ', '.join(product['flavor']) if product['flavor'] else 'Brez okusa'
        print(f"{i+1}. {package_type}: {product['brand']} - {flavors}")
        print(f"   Ime: {product['name'][:70]}...")
        print(f"   Volume: {product['volume_str']}, Match key: {product['match_key']}")
        print()

# Find matches by match_key
print("\n" + "="*80)
print("ISKANJE UJEMANJ Z RAZLIČNIMI CENAMI:")
print("="*80)

# Group products by match_key
spar_by_key = defaultdict(list)
for product in spar_products:
    spar_by_key[product['match_key']].append(product)

mercator_by_key = defaultdict(list)
for product in mercator_products:
    mercator_by_key[product['match_key']].append(product)

# Find common keys
common_keys = set(spar_by_key.keys()).intersection(set(mercator_by_key.keys()))
print(f"\nNajdenih {len(common_keys)} izdelkov z ujemajočo znamko+okusom+volumnom")

if common_keys:
    print("\nPrvih 10 skupnih match ključev:")
    for i, key in enumerate(sorted(common_keys)[:10]):
        print(f"{i+1}. {key}")

matches = []
for key in sorted(common_keys):
    spar_products_list = spar_by_key[key]
    mercator_products_list = mercator_by_key[key]
    
    for spar_product in spar_products_list:
        for mercator_product in mercator_products_list:
            # STRICT matching: brand, flavor, volume_ml AND package type must match
            # BLOOD ORANGE se zdaj ujema s POMARANČNIMI IZDELKI!
            if (spar_product['brand'] == mercator_product['brand'] and
                spar_product['flavor'] == mercator_product['flavor'] and
                spar_product['volume_ml'] == mercator_product['volume_ml'] and
                spar_product['is_package'] == mercator_product['is_package']):
                
                price_diff = spar_product['price'] - mercator_product['price']
                price_diff_percent = (price_diff / mercator_product['price']) * 100 if mercator_product['price'] > 0 else 0
                
                matches.append({
                    'match_key': key,
                    'brand': spar_product['brand'],
                    'flavor': ', '.join(spar_product['flavor']) if spar_product['flavor'] else 'N/A',
                    'volume_str': spar_product['volume_str'],
                    'volume_ml': spar_product['volume_ml'],
                    'is_package': spar_product['is_package'],
                    'package_count': spar_product['package_count'],
                    'spar_original': spar_product['original_name'],
                    'spar_name': spar_product['name'],
                    'spar_price': spar_product['price'],
                    'mercator_original': mercator_product['original_name'],
                    'mercator_name': mercator_product['name'],
                    'mercator_price': mercator_product['price'],
                    'price_difference': price_diff,
                    'price_difference_percent': price_diff_percent
                })

print(f"\nVeljavna natančna ujemanja najdena: {len(matches)}")

# Filter matches with DIFFERENT price (difference more than 0.01)
different_price_matches = [m for m in matches if abs(m['price_difference']) > 0.01]

# Display results - ONLY DIFFERENT PRICE MATCHES
if different_price_matches:
    print("\n" + "="*80)
    print(f"UJEMANJA Z RAZLIČNIMI CENAMI ({len(different_price_matches)} najdenih):")
    print("="*80)
    
    # Razvrstimo po največji razliki v ceni
    different_price_matches.sort(key=lambda x: abs(x['price_difference_percent']), reverse=True)
    
    for i, match in enumerate(different_price_matches, 1):
        package_info = f"PAKET {match['package_count']}x" if match['is_package'] else "POSAMEZNI"
        print(f"\n{i}. {match['brand']} - {match['flavor']} - {package_info} {match['volume_str']}")
        print(f"   Spar:     {match['spar_name'][:70]}...")
        print(f"            €{match['spar_price']:.2f}")
        print(f"   Mercator: {match['mercator_name'][:70]}...")
        print(f"            €{match['mercator_price']:.2f}")
        
        if match['price_difference'] > 0.01:
            print(f"   → Mercator je CENEJŠI za €{abs(match['price_difference']):.2f} ({abs(match['price_difference_percent']):.1f}%)")
        elif match['price_difference'] < -0.01:
            print(f"   → Spar je CENEJŠI za €{abs(match['price_difference']):.2f} ({abs(match['price_difference_percent']):.1f}%)")
        
        # Prikažemo match key za debugging
        print(f"   Match key: {match['match_key']}")
        
        # Če gre za blood orange izdelek, to posebej označimo
        if 'BLOOD' in match['spar_name'].upper() or 'BLOOD' in match['mercator_name'].upper():
            print(f"   ⚠️  Opomba: BLOOD ORANGE izdelek (standardiziran kot POMARANCA)")
else:
    print("\nNi najdenih ujemanj z različnimi cenami.")

