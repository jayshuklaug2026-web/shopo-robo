"""
Shopo Robo — India-Wide Industry Taxonomy System (Module 2)
============================================================
Provides an extensible, configurable taxonomy of 28+ Indian industries
with specialized product attributes, Hindi/English localized names,
natural-language business matching, and dynamic custom extension.

Industry selection configures business tools and specialized product
attributes without restricting the AI's universal general intelligence.
"""

from typing import List, Dict, Any, Optional
import re
from database import get_custom_taxonomies, save_custom_taxonomy

# ────────────────────────────────────────────────────────────
# Core 28+ Indian Industry Taxonomies
# ────────────────────────────────────────────────────────────

CORE_INDIAN_INDUSTRIES: List[Dict[str, Any]] = [
    {
        "id": "grocery_fmcg",
        "name_en": "Grocery, FMCG, and Supermarkets",
        "name_hi": "किराना, किराना स्टोर और सुपरमार्केट",
        "group": "Retail & Consumer Goods",
        "keywords": ["grocery", "kirana", "ration", "fmcg", "supermarket", "atta", "dal", "oil", "soap", "biscuit", "spices", "namkeen"],
        "description": "Daily food provisions, staples, packaged FMCG foods, personal toiletries, and household goods.",
        "attributes": [
            {"key": "mrp", "label": "MRP (₹)", "type": "number", "required": False},
            {"key": "expiry_date", "label": "Expiry Date", "type": "date", "required": False},
            {"key": "fssai_license", "label": "FSSAI License No.", "type": "text", "required": False},
            {"key": "hsn_code", "label": "HSN Code", "type": "text", "required": False},
            {"key": "net_weight", "label": "Net Weight / Volume", "type": "text", "required": False}
        ],
        "default_units": ["kg", "gram", "litre", "ml", "packet", "pouch", "bottle", "pcs"]
    },
    {
        "id": "pharmacy_medical",
        "name_en": "Pharmacy and Medical Retail",
        "name_hi": "फार्मेसी, मेडिकल और दवा स्टोर",
        "group": "Healthcare & Wellness",
        "keywords": ["pharmacy", "medical", "chemist", "medicine", "dawa", "tablet", "syrup", "capsule", "injection", "surgical", "bandage"],
        "description": "Retail pharmaceutical distribution, OTC medicines, surgical disposables, Schedule H/H1 drugs, and health supplements.",
        "attributes": [
            {"key": "batch_number", "label": "Batch Number", "type": "text", "required": True},
            {"key": "expiry_date", "label": "Expiry Date", "type": "date", "required": True},
            {"key": "salt_composition", "label": "Salt / Generic Composition", "type": "text", "required": False},
            {"key": "drug_schedule", "label": "Drug Schedule (OTC/H/H1/X)", "type": "select", "options": ["OTC", "Schedule H", "Schedule H1", "Schedule X"], "required": False},
            {"key": "mfg_license", "label": "Mfg License No.", "type": "text", "required": False}
        ],
        "default_units": ["strip", "bottle", "box", "vial", "tube", "pcs"]
    },
    {
        "id": "healthcare_services",
        "name_en": "Healthcare Businesses and Clinics",
        "name_hi": "स्वास्थ्य सेवाएं, क्लीनिक और डायग्नोस्टिक्स",
        "group": "Healthcare & Wellness",
        "keywords": ["clinic", "hospital", "doctor", "pathology", "diagnostic", "dental", "nursing", "ambulance", "lab tests"],
        "description": "Outpatient consultation, diagnostic pathology services, dental clinics, and wellness care centers.",
        "attributes": [
            {"key": "service_code", "label": "Service / Procedure Code", "type": "text", "required": False},
            {"key": "doctor_department", "label": "Specialty / Department", "type": "text", "required": False},
            {"key": "consultation_fee", "label": "Standard Fee (₹)", "type": "number", "required": False}
        ],
        "default_units": ["consultation", "test", "visit", "package", "procedure"]
    },
    {
        "id": "hardware_tools",
        "name_en": "Hardware and Construction Materials",
        "name_hi": "हार्डवेयर, औजार और निर्माण सामग्री",
        "group": "Construction & Industrial",
        "keywords": ["hardware", "tools", "fasteners", "screws", "drills", "plywood", "laminate", "sanitary", "faucets", "fittings", "taar", "killi"],
        "description": "Tools, hand tools, power tools, brass and stainless fasteners, sanitary fittings, and carpentry hardware.",
        "attributes": [
            {"key": "dimensions", "label": "Dimensions (Size / Length / Dia)", "type": "text", "required": False},
            {"key": "material_grade", "label": "Material Grade (SS304/Brass/MS)", "type": "text", "required": False},
            {"key": "gauge", "label": "Gauge / Thickness", "type": "text", "required": False}
        ],
        "default_units": ["pcs", "box", "dozen", "packet", "set", "kg"]
    },
    {
        "id": "cement_steel_paints",
        "name_en": "Cement, Steel, Paint, Pipes, and Electrical Supplies",
        "name_hi": "सीमेंट, सरिया (स्टील), पेंट, पाइप और बिजली का सामान",
        "group": "Construction & Industrial",
        "keywords": ["cement", "sariya", "steel", "tmt", "paint", "pipe", "pvc", "wire", "switch", "mcb", "cable", "conduit"],
        "description": "Primary structural materials: TMT rebars, structural steel sections, OPC/PPC cement bags, architectural paints, CPVC plumbing, and wires.",
        "attributes": [
            {"key": "grade", "label": "Grade (Fe550D / 53 Grade / SCH40)", "type": "text", "required": False},
            {"key": "diameter_mm", "label": "Diameter (mm) / Size", "type": "text", "required": False},
            {"key": "color_shade", "label": "Shade Code / Finish", "type": "text", "required": False},
            {"key": "standard_cert", "label": "Standard (IS 1786 / IS 269)", "type": "text", "required": False}
        ],
        "default_units": ["bag", "MT", "bundle", "metre", "coil", "litre", "tin", "pcs"]
    },
    {
        "id": "textile_fashion",
        "name_en": "Textile, Clothing, Fashion, and Apparel",
        "name_hi": "कपड़ा, परिधान, गारमेंट्स और फैशन",
        "group": "Fashion & Lifestyle",
        "keywords": ["textile", "kapda", "saree", "suit", "shirt", "pant", "jeans", "garment", "fabric", "cotton", "silk", "readymade", "kurti"],
        "description": "Textile fabrics, unstitched suit materials, sarees, readymade garments, hosiery, and fashion accessories.",
        "attributes": [
            {"key": "size", "label": "Size (S/M/L/XL / 38/40/42)", "type": "text", "required": False},
            {"key": "fabric_type", "label": "Fabric (Cotton/Rayon/Silk)", "type": "text", "required": False},
            {"key": "color_pattern", "label": "Color / Pattern", "type": "text", "required": False},
            {"key": "gender_target", "label": "Target (Men/Women/Kids/Unisex)", "type": "select", "options": ["Men", "Women", "Kids", "Unisex"], "required": False}
        ],
        "default_units": ["pcs", "metre", "pair", "set", "roll", "than"]
    },
    {
        "id": "electronics_mobiles",
        "name_en": "Electronics, Mobiles, and Computers",
        "name_hi": "इलेक्ट्रॉनिक्स, मोबाइल फोन और कंप्यूटर",
        "group": "Consumer Technology",
        "keywords": ["mobile", "electronics", "laptop", "computer", "smartphone", "charger", "tv", "refrigerator", "earphones", "tablet"],
        "description": "Consumer electronics, smart phones, mobile accessories, computers, IT peripherals, home entertainment, and refrigeration.",
        "attributes": [
            {"key": "imei_serial", "label": "IMEI / Serial Number", "type": "text", "required": False},
            {"key": "model_number", "label": "Model Number", "type": "text", "required": False},
            {"key": "warranty_months", "label": "Warranty Period (Months)", "type": "number", "required": False},
            {"key": "specifications", "label": "Specs (RAM/ROM/Storage)", "type": "text", "required": False}
        ],
        "default_units": ["pcs", "box", "set"]
    },
    {
        "id": "automobile_spareparts",
        "name_en": "Automobile Dealers and Spare Parts",
        "name_hi": "ऑटोमोबाइल डीलर, गैरेज और स्पेयर पार्ट्स",
        "group": "Automotive & Transport",
        "keywords": ["automobile", "auto parts", "bike", "car", "tyre", "battery", "clutch", "brake pad", "engine oil", "spare parts", "garage"],
        "description": "Two-wheeler and four-wheeler spare parts, automotive batteries, lubricants, brake pads, tyres, filters, and dealership services.",
        "attributes": [
            {"key": "part_number", "label": "OEM / Part Number", "type": "text", "required": False},
            {"key": "compatible_vehicle", "label": "Vehicle Compatibility", "type": "text", "required": False},
            {"key": "warranty_months", "label": "Warranty (Months)", "type": "number", "required": False}
        ],
        "default_units": ["pcs", "set", "pair", "litre", "box"]
    },
    {
        "id": "agriculture_inputs",
        "name_en": "Agriculture, Farming, Seeds, Fertilizers, and Inputs",
        "name_hi": "कृषि, बीज, खाद (उर्वरक), कीटनाशक और कृषि उपकरण",
        "group": "Agriculture & Rural",
        "keywords": ["agriculture", "seeds", "fertilizer", "kisan", "beej", "khad", "urea", "dap", "pesticide", "spray", "tractor", "farming"],
        "description": "Agricultural inputs: certified hybrid seeds, chemical & organic fertilizers, insecticides, fungicides, drip irrigation, and sprayers.",
        "attributes": [
            {"key": "subsidy_eligible", "label": "Govt Subsidy Eligible", "type": "boolean", "required": False},
            {"key": "germination_pct", "label": "Min Germination (%)", "type": "text", "required": False},
            {"key": "npk_ratio", "label": "NPK Ratio (e.g. 19:19:19)", "type": "text", "required": False},
            {"key": "batch_and_expiry", "label": "Seed/Chemical Batch & Expiry", "type": "text", "required": False}
        ],
        "default_units": ["kg", "bag", "litre", "bottle", "packet", "quintal"]
    },
    {
        "id": "commodity_trading",
        "name_en": "Agricultural Commodity Trading (Mandi & Wholesale)",
        "name_hi": "मंडी व्यापार, कृषि जिंस और थोक आढ़त",
        "group": "Agriculture & Rural",
        "keywords": ["mandi", "arhat", "apmc", "commodity", "grain", "wheat", "paddy", "mustard", "soybean", "cotton", "auction", "trader"],
        "description": "Wholesale APMC mandi commission agents, grain traders, oilseed merchants, pulses brokers, and commodity auction houses.",
        "attributes": [
            {"key": "moisture_content", "label": "Moisture Content (%)", "type": "text", "required": False},
            {"key": "crop_season", "label": "Season (Kharif / Rabi / Zaid)", "type": "select", "options": ["Kharif", "Rabi", "Zaid"], "required": False},
            {"key": "mandi_mandi_lot", "label": "Lot / Dheri No.", "type": "text", "required": False}
        ],
        "default_units": ["quintal", "MT", "borah", "bag", "kg"]
    },
    {
        "id": "dairy_livestock",
        "name_en": "Dairy, Livestock, and Animal Supplies",
        "name_hi": "डेयरी, पशुपालन, चारा और पशु आहार",
        "group": "Agriculture & Rural",
        "keywords": ["dairy", "doodh", "milk", "paneer", "cattle", "pashu aahar", "chana churi", "animal feed", "ghee", "poultry", "murgi"],
        "description": "Milk collection centres, packaged dairy production, animal feeds, poultry feed supplements, and veterinary health items.",
        "attributes": [
            {"key": "fat_snf", "label": "Fat % / SNF %", "type": "text", "required": False},
            {"key": "pasteurization_temp", "label": "Cold Storage Required", "type": "boolean", "required": False},
            {"key": "feed_protein_pct", "label": "Crude Protein (%)", "type": "text", "required": False}
        ],
        "default_units": ["litre", "kg", "bag", "can", "packet"]
    },
    {
        "id": "manufacturing_industrial",
        "name_en": "Manufacturing and Industrial Production",
        "name_hi": "विनिर्माण, फैक्ट्री और औद्योगिक उत्पादन",
        "group": "Manufacturing & Engineering",
        "keywords": ["factory", "manufacturing", "production", "raw material", "machine", "fabrication", "assembly", "tooling", "packaging plant"],
        "description": "Light and heavy industrial production, contract manufacturing, component machining, processing units, and fabrication works.",
        "attributes": [
            {"key": "raw_material_type", "label": "Primary Raw Material", "type": "text", "required": False},
            {"key": "batch_lot", "label": "Production Batch / Lot", "type": "text", "required": False},
            {"key": "lead_time_days", "label": "Production Lead Time (Days)", "type": "number", "required": False}
        ],
        "default_units": ["unit", "pcs", "MT", "batch", "hour", "lot"]
    },
    {
        "id": "wholesale_trading",
        "name_en": "Wholesale, Distribution, and Trading",
        "name_hi": "थोक व्यापार, डिस्ट्रीब्यूटरशिप और ट्रेडिंग",
        "group": "Wholesale & Logistics",
        "keywords": ["wholesale", "distributor", "stockist", "dealer", "bulk", "c&f", "agency", "godown", "carton", "b2b"],
        "description": "B2B stockists, carry and forwarding (C&F) agencies, wholesale bulk merchants, and regional distributors.",
        "attributes": [
            {"key": "moq", "label": "Minimum Order Quantity (MOQ)", "type": "number", "required": False},
            {"key": "case_pack", "label": "Units Per Master Carton", "type": "number", "required": False},
            {"key": "distributor_margin_pct", "label": "Trade Margin (%)", "type": "number", "required": False}
        ],
        "default_units": ["carton", "box", "case", "pallet", "MT", "gross"]
    },
    {
        "id": "restaurant_foodservices",
        "name_en": "Restaurants, Catering, and Food Services",
        "name_hi": "रेस्टोरेंट, ढाबा, हलवाई, बेकरी और खान-पान सेवा",
        "group": "Food & Hospitality",
        "keywords": ["restaurant", "cafe", "dhaba", "sweet shop", "halwai", "catering", "bakery", "fast food", "kitchen", "biryani", "thali"],
        "description": "Dine-in restaurants, cloud kitchens, dhabas, sweet shops (halwai), bakeries, and outdoor catering services.",
        "attributes": [
            {"key": "prep_time_mins", "label": "Prep Time (Minutes)", "type": "number", "required": False},
            {"key": "food_category", "label": "Dietary (Veg/Non-Veg/Vegan)", "type": "select", "options": ["Pure Veg", "Non-Veg", "Egg", "Jain"], "required": False},
            {"key": "shelf_life_hours", "label": "Prepared Shelf Life (Hours)", "type": "number", "required": False}
        ],
        "default_units": ["plate", "portion", "kg", "pcs", "thali", "box"]
    },
    {
        "id": "hospitality_tourism",
        "name_en": "Hotels, Tourism, and Hospitality",
        "name_hi": "होटल, लॉज, होमस्टे, पर्यटन और अतिथि सत्कार",
        "group": "Food & Hospitality",
        "keywords": ["hotel", "lodge", "resort", "homestay", "tour", "travel", "rooms", "booking", "guest house"],
        "description": "Hotels, budget lodges, tourist homestays, tour operators, travel agents, and corporate event venues.",
        "attributes": [
            {"key": "room_type", "label": "Room / Service Type (AC/Non-AC/Deluxe)", "type": "text", "required": False},
            {"key": "max_occupancy", "label": "Max Guests", "type": "number", "required": False},
            {"key": "checkout_hours", "label": "Check-out Rules", "type": "text", "required": False}
        ],
        "default_units": ["night", "room", "package", "person", "day"]
    },
    {
        "id": "real_estate_property",
        "name_en": "Real Estate and Property-Related Businesses",
        "name_hi": "रियल एस्टेट, प्रॉपर्टी डीलर, ब्रोकरेज और कंस्ट्रक्शन",
        "group": "Property & Services",
        "keywords": ["real estate", "property", "dealer", "plot", "flat", "rent", "brokerage", "land", "developer", "registry"],
        "description": "Property consulting, real estate brokerage, residential/commercial leasing, land development, and plot sales.",
        "attributes": [
            {"key": "carpet_area_sqft", "label": "Carpet / Plot Area (sq.ft / Gaj)", "type": "text", "required": False},
            {"key": "rera_registered", "label": "RERA Registration Number", "type": "text", "required": False},
            {"key": "property_type", "label": "Property Type (Residential/Commercial/Plot/Shop)", "type": "text", "required": False}
        ],
        "default_units": ["sq.ft", "sq.yard (gaj)", "bigha", "acre", "unit", "flat"]
    },
    {
        "id": "furniture_home_appliances",
        "name_en": "Furniture and Home Appliances",
        "name_hi": "फर्नीचर, लकड़ी का काम और घरेलू उपकरण",
        "group": "Consumer Goods & Living",
        "keywords": ["furniture", "sofa", "bed", "table", "chair", "almirah", "cooler", "fan", "mattress", "kitchenware", "curtains"],
        "description": "Wooden, metal and plastic furniture, sleep mattresses, desert coolers, fans, kitchen appliances, and furnishings.",
        "attributes": [
            {"key": "dimensions_cm", "label": "Dimensions (L x W x H cm)", "type": "text", "required": False},
            {"key": "wood_material", "label": "Material (Teak/Sheesham/MDF/Steel)", "type": "text", "required": False},
            {"key": "warranty_years", "label": "Warranty (Years)", "type": "number", "required": False}
        ],
        "default_units": ["pcs", "set", "pair"]
    },
    {
        "id": "beauty_personal_care",
        "name_en": "Beauty, Cosmetics, and Personal Care",
        "name_hi": "सौंदर्य प्रसाधन, सैलून, ब्यूटी पार्लर और कॉस्मेटिक्स",
        "group": "Fashion & Lifestyle",
        "keywords": ["beauty", "cosmetics", "salon", "parlour", "cream", "lipstick", "perfume", "skincare", "haircut", "facial"],
        "description": "Cosmetic retail shops, beauty salons, barber services, skincare products, hair wellness, and herbal treatments.",
        "attributes": [
            {"key": "skin_hair_type", "label": "Skin / Hair Compatibility", "type": "text", "required": False},
            {"key": "organic_ayurvedic", "label": "Certified Ayurvedic / Herbal", "type": "boolean", "required": False},
            {"key": "volume_weight", "label": "Net Pack Size", "type": "text", "required": False}
        ],
        "default_units": ["pcs", "bottle", "tube", "service", "pack"]
    },
    {
        "id": "books_stationery_education",
        "name_en": "Books, Stationery, and Educational Supplies",
        "name_hi": "किताबें, स्टेशनरी, स्कूल का सामान और कोचिंग",
        "group": "Education & Media",
        "keywords": ["books", "stationery", "kitab", "copy", "notebook", "pen", "pencil", "school bag", "uniform", "coaching", "exam notes"],
        "description": "Educational textbooks, NCERT guides, competitive exam study materials, notebooks, pens, school kits, and office stationery.",
        "attributes": [
            {"key": "isbn_code", "label": "ISBN Code", "type": "text", "required": False},
            {"key": "author_publisher", "label": "Author / Board / Publisher", "type": "text", "required": False},
            {"key": "edition_year", "label": "Edition / Academic Session", "type": "text", "required": False}
        ],
        "default_units": ["pcs", "book", "set", "packet", "bundle", "dozen"]
    },
    {
        "id": "it_services_digital",
        "name_en": "IT Services, Software, and Digital Businesses",
        "name_hi": "आईटी सेवाएं, सॉफ्टवेयर, वेबसाइट और डिजिटल बिजनेस",
        "group": "Technology & Media",
        "keywords": ["software", "it services", "web development", "mobile app", "cyber cafe", "digital marketing", "seo", "hosting", "saas"],
        "description": "Software development firms, freelance developers, web design studios, cyber cafes, digital marketing agencies, and SaaS providers.",
        "attributes": [
            {"key": "billing_model", "label": "Billing (Hourly / Fixed / Retainer)", "type": "text", "required": False},
            {"key": "sla_response", "label": "SLA Support Level", "type": "text", "required": False},
            {"key": "stack_technology", "label": "Technology Stack", "type": "text", "required": False}
        ],
        "default_units": ["hour", "project", "subscription/month", "milestone", "ticket"]
    },
    {
        "id": "ecommerce_online_retail",
        "name_en": "E-Commerce and Online Retail (D2C)",
        "name_hi": "ई-कॉमर्स, ऑनलाइन सेलिंग और डायरेक्ट-टू-कंज्यूमर",
        "group": "Retail & Consumer Goods",
        "keywords": ["ecommerce", "online store", "amazon", "flipkart", "meesho", "shopify", "d2c", "dropshipping", "parcel"],
        "description": "Direct-to-consumer online brands, Amazon/Flipkart/Meesho sellers, social commerce retailers, and drop-shippers.",
        "attributes": [
            {"key": "sku_online", "label": "Marketplace Listing SKU", "type": "text", "required": False},
            {"key": "weight_dead_volumetric", "label": "Shipping Volumetric Weight (g)", "type": "number", "required": False},
            {"key": "fulfillment_type", "label": "Fulfillment (FBA/FBF/Self-Ship)", "type": "text", "required": False}
        ],
        "default_units": ["order", "item", "package", "consignment"]
    },
    {
        "id": "logistics_transport_warehousing",
        "name_en": "Logistics, Transportation, and Warehousing",
        "name_hi": "लॉजिस्टिक्स, ट्रांसपोर्ट, माल ढुलाई और गोदाम (वेयरहाउसिंग)",
        "group": "Wholesale & Logistics",
        "keywords": ["transport", "logistics", "truck", "tempo", "courier", "freight", "godown", "warehouse", "cold storage", "bilty"],
        "description": "Road freight operators, mini-truck aggregators, parcel courier agencies, commercial warehouses, and rural cold storage units.",
        "attributes": [
            {"key": "vehicle_type", "label": "Vehicle Category (Tata Ace / 14-Wheeler)", "type": "text", "required": False},
            {"key": "weight_capacity_mt", "label": "Payload Capacity (MT / kg)", "type": "number", "required": False},
            {"key": "eway_bill_supported", "label": "E-Way Bill Integration", "type": "boolean", "required": False}
        ],
        "default_units": ["trip", "km", "MT", "pallet/month", "parcel", "consignment"]
    },
    {
        "id": "energy_solar_electrical",
        "name_en": "Energy, Solar, Batteries, and Electrical Products",
        "name_hi": "सौर ऊर्जा (सोलर), इन्वर्टर, बैटरी और विद्युत उत्पाद",
        "group": "Energy & Infrastructure",
        "keywords": ["solar", "solar panel", "battery", "inverter", "generator", "rooftop solar", "lithium", "solar pump", "stabilizer"],
        "description": "Rooftop solar EPC installers, tubular inverter batteries, UPS systems, diesel generators, solar water pumps, and power backup.",
        "attributes": [
            {"key": "capacity_watt_ah", "label": "Capacity (Watts / Ah / kVA)", "type": "text", "required": False},
            {"key": "technology_type", "label": "Tech (Mono PERC / Tubular / LiFePO4)", "type": "text", "required": False},
            {"key": "subsidy_pm_surya", "label": "PM Surya Ghar Subsidy Approved", "type": "boolean", "required": False},
            {"key": "warranty_years", "label": "Warranty (Years)", "type": "number", "required": False}
        ],
        "default_units": ["set", "pcs", "kW", "unit", "system"]
    },
    {
        "id": "chemicals_industrial_supplies",
        "name_en": "Chemicals and Industrial Supplies",
        "name_hi": "रसायन (केमिकल्स), औद्योगिक सॉल्वैंट्स और डाइज",
        "group": "Manufacturing & Engineering",
        "keywords": ["chemicals", "acid", "solvent", "dye", "cleaning agent", "industrial chemical", "bleach", "caustic soda", "polymer"],
        "description": "Industrial chemicals, textile dyes, laboratory reagents, polymers, solvents, acids, and institutional cleaning compounds.",
        "attributes": [
            {"key": "purity_percentage", "label": "Purity Grade (%)", "type": "text", "required": False},
            {"key": "cas_number", "label": "CAS / UN Hazard Code", "type": "text", "required": False},
            {"key": "msds_available", "label": "Safety Data Sheet (MSDS) Available", "type": "boolean", "required": False}
        ],
        "default_units": ["drum", "carboy", "barrel", "kg", "litre", "MT"]
    },
    {
        "id": "handicrafts_cottage_industry",
        "name_en": "Handicrafts and Small-Scale Industries (MSME / Khadi)",
        "name_hi": "हस्तशिल्प, कुटीर उद्योग, खादी और पारंपरिक शिल्प",
        "group": "Artisans & Small Enterprises",
        "keywords": ["handicraft", "khadi", "handloom", "pottery", "clay", "wood carving", "embroidery", "artisan", "cottage industry", "jute"],
        "description": "Artisanal woodwork, pottery, handloom textiles, brass artifacts, jute bags, village industries, and PM Vishwakarma craft businesses.",
        "attributes": [
            {"key": "artisan_craft_type", "label": "Craft Heritage / GI Tag Name", "type": "text", "required": False},
            {"key": "vishwakarma_scheme", "label": "PM Vishwakarma Registered", "type": "boolean", "required": False},
            {"key": "handmade_cert", "label": "100% Handcrafted Certified", "type": "boolean", "required": False}
        ],
        "default_units": ["pcs", "set", "pair", "lot"]
    },
    {
        "id": "professional_consulting",
        "name_en": "Professional and Consulting Services",
        "name_hi": "व्यावसायिक परामर्श, सीए, लीगल और कंसल्टिंग",
        "group": "Professional Services",
        "keywords": ["consultant", "chartered accountant", "advocate", "lawyer", "architect", "engineer", "gst practitioner", "tax audit"],
        "description": "Chartered accountancy firms, tax consultants, legal advocates, structural engineers, architects, and business advisors.",
        "attributes": [
            {"key": "professional_council_id", "label": "Council Registration No. (ICAI/BCI/COA)", "type": "text", "required": False},
            {"key": "service_scope", "label": "Specialization (GST/Income Tax/Litigation)", "type": "text", "required": False}
        ],
        "default_units": ["filing", "audit", "hour", "session", "retainer/month"]
    },
    {
        "id": "finance_accounting_support",
        "name_en": "Finance, Microfinance, and Accounting Support",
        "name_hi": "फाइनेंस, माइक्रोफाइनेंस, बीमा और मुनीमी सहायता",
        "group": "Financial Services",
        "keywords": ["finance", "loan", "microfinance", "insurance", "bima", "accounting", "bookkeeping", "pos machine", "khatabook", "bahi khata"],
        "description": "Direct sales agencies for retail loans, microfinance institutions, general insurance agents, and traditional bahi-khata accountants.",
        "attributes": [
            {"key": "partner_bank_nbfc", "label": "Partner Bank / NBFC / Insurer", "type": "text", "required": False},
            {"key": "irda_amfi_arn", "label": "ARN / IRDAI License No.", "type": "text", "required": False}
        ],
        "default_units": ["policy", "disbursal", "account", "case", "file"]
    },
    {
        "id": "custom_other_industry",
        "name_en": "Other and Custom Indian Businesses",
        "name_hi": "अन्य और कस्टम भारतीय व्यापार",
        "group": "Custom & Emerging",
        "keywords": ["custom", "other", "general", "new business", "start-up", "local business", "vyapar"],
        "description": "Any innovative, specialized, rural, or unlisted trade in the dynamic Indian commercial landscape.",
        "attributes": [
            {"key": "custom_spec", "label": "Custom Specification / Note", "type": "text", "required": False}
        ],
        "default_units": ["unit", "pcs", "kg", "litre", "service", "item"]
    }
]


# ────────────────────────────────────────────────────────────
# Taxonomy API & Natural Language Matcher
# ────────────────────────────────────────────────────────────

def get_all_taxonomies() -> List[Dict[str, Any]]:
    """Return all core taxonomies combined with any custom user/admin created taxonomies."""
    custom_list = get_custom_taxonomies()
    # Map custom into standard taxonomy dicts
    custom_formatted = []
    for c in custom_list:
        custom_formatted.append({
            "id": c["id"],
            "name_en": c["name_en"],
            "name_hi": c["name_hi"] or c["name_en"],
            "group": c["category_group"] or "Custom Industry",
            "keywords": [w.lower() for w in re.split(r'\W+', f"{c['name_en']} {c['description']}") if len(w) > 2],
            "description": c["description"] or "User-defined custom industry category.",
            "attributes": c.get("attributes", []),
            "default_units": ["unit", "pcs", "kg", "service"],
            "is_custom": True,
            "created_at": c.get("created_at")
        })

    return CORE_INDIAN_INDUSTRIES + custom_formatted


def get_taxonomy_by_id(tax_id: str) -> Optional[Dict[str, Any]]:
    """Find a taxonomy by ID (slug)."""
    for item in get_all_taxonomies():
        if item["id"] == tax_id:
            return item
    return None


def match_industry_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Intelligently match one or more industries from natural language description.
    Supports Hindi, Hinglish, and English terms.
    """
    if not text or not text.strip():
        return [CORE_INDIAN_INDUSTRIES[0]]  # Default to grocery/fmcg

    lower = text.lower()
    scored: List[tuple[int, Dict[str, Any]]] = []

    all_tax = get_all_taxonomies()
    for tax in all_tax:
        score = 0
        # Check taxonomy title matches
        if tax["id"].replace('_', ' ') in lower:
            score += 10
        if tax["name_en"].lower() in lower:
            score += 15
        if tax.get("name_hi") and tax["name_hi"] in text:
            score += 15

        # Check keywords
        for kw in tax.get("keywords", []):
            if kw.lower() in lower:
                score += 4

        # Check description words
        desc_words = [w.lower() for w in re.split(r'\W+', tax.get("description", "")) if len(w) > 4]
        for dw in desc_words:
            if dw in lower:
                score += 1

        if score > 0:
            scored.append((score, tax))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)

    if scored:
        # Return top matches (threshold score >= 2)
        top = [item for sc, item in scored if sc >= 2]
        return top[:3] if top else [scored[0][1]]

    # If no match, return the custom/other category
    return [get_taxonomy_by_id("custom_other_industry") or CORE_INDIAN_INDUSTRIES[-1]]


def add_custom_industry(name_en: str, name_hi: str = "", description: str = "", category_group: str = "custom", attributes: list = None) -> Dict[str, Any]:
    """Extends the taxonomy without modifying code."""
    res = save_custom_taxonomy(name_en, name_hi, description, category_group, attributes)
    return res
