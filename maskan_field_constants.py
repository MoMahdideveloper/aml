# -*- coding: utf-8 -*-
"""
Maskan-file.ir Property Form Constants
Extracted from https://maskan-file.ir/Site/InsertFileAmlak.aspx
These constant values match the maskan-file.ir platform for data compatibility.
"""

# ========================================
# DROPDOWN FIELD CONSTANTS
# ========================================

# نوع واگذاری - Transfer Type
TRANSFER_TYPES = {
    "sale": "فروش",
    "rent": "رهن و اجاره",
}

# نوع ملک - Property Type
PROPERTY_TYPES = {
    "apartment": "آپارتمان",
    "office": "دفتر کار",
    "villa": "ویلایی",
    "shop": "مغازه",
    "land": "زمین",
}

# نوع سند - Document Type
DOCUMENT_TYPES = {
    "full_deed": "شش دانگ",
    "private_deed": "شش دانگ ملکی",
    "astaneh_deed": "شش دانگ آستانه",
    "endowment_deed": "شش دانگ اوقاف",
    "razavi_deed": "شش دانگ رضوی",
    "half_deed": "سه دانگ",
    "proxy": "وکالتی",
    "agreement": "قولنامه ای",
}

# دیوارپوش - Wall Covering
WALL_COVERINGS = {
    "unknown": "نامشخص",
    "wallpaper": "کاغذ دیواری",
    "painting": "نقاشی",
    "plaster": "گچ",
    "paneling": "پنل کوبی",
    "wood": "چوب",
    "3d": "سه بعدی",
    "composite_fiber": "الیاف ترکیبی",
    "tile": "کاشی",
    "stone": "سنگ",
    "other": "غیره",
    "customer_choice": "سلیقه مشتری",
}

# کابینت - Cabinet
CABINET_TYPES = {
    "unknown": "نامشخص",
    "mdf": "ام دی اف",
    "metal": "فلز",
    "high_gloss": "های گلس",
    "mdf_design": "طرح ام دی اف",
    "vacuum": "وکیوم",
    "melamine": "ملامینه",
    "wood": "چوب",
    "wood_veneer": "روکش چوب",
    "none": "ندارد",
    "customer_choice": "سلیقه مشتری",
}

# سرمایش - Cooling System
COOLING_SYSTEMS = {
    "unknown": "نامشخص",
    "water_cooler": "کولرآبی",
    "air_conditioner": "کولر گازی",
    "air_handler": "هواساز",
}

# گرمایش - Heating System
HEATING_SYSTEMS = {
    "unknown": "نامشخص",
    "heater": "بخاری",
    "package": "پکیج",
    "air_handler": "هواساز",
    "underfloor": "گرمایش از کف",
    "fireplace": "شومینه",
}

# کفپوش - Flooring
FLOORING_TYPES = {
    "unknown": "نامشخص",
    "ceramic": "سرامیک",
    "parquet": "پارکت",
    "carpet": "موکت",
    "flooring": "کفپوش",
    "stone": "سنگ",
    "cement": "سیمان",
    "mosaic": "موزاییک",
    "pvc": "پی وی سی",
    "customer_choice": "سلیقه مشتری",
}

# نما - View/Facade
FACADE_TYPES = {
    "unknown": "نامشخص",
    "stone": "سنگ",
    "brick_3cm": "آجر سه سانت",
    "ceramic": "سرامیک",
    "brick": "آجر",
    "cement": "سیمان",
    "composite": "کامپوزیت",
    "aluminum": "آلومینیوم",
    "glass": "شیشه",
    "stone_brick": "سنگ و آجر",
    "roman": "رومی",
    "other": "غیره",
}

# جهت ملک - Direction
DIRECTIONS = {
    "north": "شمالی",
    "south": "جنوبی",
    "two_sided": "دونبش",
    "two_way": "دوممر",
    "east": "شرقی",
    "west": "غربی",
    "east_west": "شرقی/غربی",
}

# ========================================
# BOOLEAN/CHECKBOX FEATURES (امکانات ملک)
# ========================================

PROPERTY_FEATURES = {
    "renovated": "بازسازی شده",
    "elevator": "آسانسور",
    "parking": "پارکینگ",
    "storage": "انباری",
    "cctv": "دوربین مداربسته",
    "hood": "هود",
    "electric_door": "درب برقی",
    "anti_theft_door": "درب ضد سرقت",
    "accordion_door": "درب آکاردئونی",
    "video_intercom": "آیفون تصویری",
    "western_toilet": "سرویس فرنگی",
}

# ========================================
# FORM FIELD IDS (for maskan-file.ir API mapping)
# ========================================

MASKAN_FIELD_IDS = {
    "wall_covering": "ContentPlaceHolder1_listWallCover",
    "cabinet": "ContentPlaceHolder1_listCabinet",
    "cooling": "ContentPlaceHolder1_listCooling",
    "heating": "ContentPlaceHolder1_listHeating",
    "flooring": "ContentPlaceHolder1_listKafpoosh",
    "document_type": "ContentPlaceHolder1_listDocType",
    "property_type": "ContentPlaceHolder1_listHouseType",
    "transfer_type": "ContentPlaceHolder1_listType",
    "facade": "ContentPlaceHolder1_listView",
    "direction": "ContentPlaceHolder1_listDirection",
    "city": "ContentPlaceHolder1_listCity",
    "region": "ContentPlaceHolder1_listStreet",
}

# ========================================
# HELPER: Get all constants as a dict for JS/API
# ========================================

def get_all_constants():
    """Return all constant field values for use in templates and APIs."""
    return {
        "transfer_types": TRANSFER_TYPES,
        "property_types": PROPERTY_TYPES,
        "document_types": DOCUMENT_TYPES,
        "wall_coverings": WALL_COVERINGS,
        "cabinet_types": CABINET_TYPES,
        "cooling_systems": COOLING_SYSTEMS,
        "heating_systems": HEATING_SYSTEMS,
        "flooring_types": FLOORING_TYPES,
        "facade_types": FACADE_TYPES,
        "directions": DIRECTIONS,
        "property_features": PROPERTY_FEATURES,
    }


def get_persian_label(field_type, key):
    """Get the Persian label for a field type and key.
    
    Example: get_persian_label('cabinet_types', 'mdf') → 'ام دی اف'
    """
    constants = get_all_constants()
    field = constants.get(field_type, {})
    return field.get(key, key)


def get_english_key(field_type, persian_value):
    """Get the English key for a field type and Persian value.
    
    Example: get_english_key('cabinet_types', 'ام دی اف') → 'mdf'
    """
    constants = get_all_constants()
    field = constants.get(field_type, {})
    for key, value in field.items():
        if value == persian_value:
            return key
    return persian_value
