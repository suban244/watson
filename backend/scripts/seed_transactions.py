"""
Seed the database with 100 expense transactions for testing full-text search.
Usage (from repo root):
    uv run python backend/scripts/seed_transactions.py
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "http://localhost:8000/api/v1/transactions/"

TRANSACTIONS = [
    # food
    (
        "Grocery shopping at Whole Foods",
        "food",
        "Weekly grocery run, fruits vegetables and dairy",
    ),
    ("Coffee at Blue Bottle Coffee", "food", "Morning espresso and almond croissant"),
    ("Lunch at Chipotle", "food", "Burrito bowl with guacamole and chips"),
    ("Dinner at Nobu restaurant", "food", "Omakase dinner for special occasion"),
    ("Pizza delivery from Dominos", "food", "Large pepperoni pizza and garlic bread"),
    ("Sushi takeout from Sakura", "food", "Friday night sushi and miso soup"),
    ("Brunch at The Egg Shop", "food", "Eggs benedict and fresh orange juice"),
    ("Taco Tuesday street food", "food", "Carne asada tacos from the food cart"),
    (
        "Smoothie bar after gym",
        "food",
        "Protein smoothie with banana and peanut butter",
    ),
    ("Late night snacks from 7-Eleven", "food", "Chips crisps and energy drink"),
    (
        "Farmers market fruit and veg",
        "food",
        "Seasonal vegetables and fresh strawberries",
    ),
    ("Meal prep ingredients", "food", "Chicken breast rice and broccoli for the week"),
    ("Starbucks coffee and sandwich", "food", "Caramel latte and turkey sandwich"),
    ("Indian takeout curry night", "food", "Butter chicken and garlic naan delivery"),
    ("Bakery croissants and bread", "food", "Sourdough loaf and assorted pastries"),
    # transport
    (
        "Uber ride to the airport",
        "transport",
        "Early morning ride to international terminal",
    ),
    ("Monthly metro card top-up", "transport", "Public transit pass for the month"),
    ("Lyft pool commute to office", "transport", "Daily morning commute shared ride"),
    (
        "Parking fee downtown garage",
        "transport",
        "All day parking in city center garage",
    ),
    (
        "Bike service and tune-up",
        "transport",
        "Annual bike maintenance brake pads and chain",
    ),
    ("Highway toll charges", "transport", "Weekend road trip toll fees"),
    ("Car wash full detailing", "transport", "Interior and exterior full service wash"),
    ("Train ticket to Boston", "transport", "Amtrak express round trip ticket"),
    ("Weekly bus pass", "transport", "City bus weekly travel card"),
    ("Electric scooter rental", "transport", "Lime scooter rental downtown"),
    # entertainment
    (
        "Netflix monthly subscription",
        "entertainment",
        "Streaming subscription for movies and shows",
    ),
    ("Spotify premium plan", "entertainment", "Monthly music and podcast streaming"),
    (
        "Cinema tickets Friday night",
        "entertainment",
        "Two tickets for new blockbuster film",
    ),
    ("Steam game purchase", "entertainment", "New RPG game on PC platform"),
    (
        "Concert tickets live music",
        "entertainment",
        "Rock concert at Madison Square Garden",
    ),
    (
        "Board game night purchase",
        "entertainment",
        "Catan and Ticket to Ride expansion packs",
    ),
    (
        "Museum natural history visit",
        "entertainment",
        "Family tickets to natural history museum",
    ),
    ("Kindle ebook bundle", "entertainment", "Three fiction novels downloaded"),
    (
        "Museum annual membership",
        "entertainment",
        "Yearly pass to art and science museums",
    ),
    ("Escape room booking", "entertainment", "Group escape room experience downtown"),
    # health
    ("Gym monthly membership fee", "health", "Monthly CrossFit gym membership"),
    ("Doctor visit annual checkup", "health", "Annual physical examination co-pay"),
    ("Dental cleaning appointment", "health", "Biannual teeth cleaning and x-ray"),
    (
        "Pharmacy vitamins and supplements",
        "health",
        "Vitamin D omega-3 and multivitamins",
    ),
    (
        "Eye exam and new glasses",
        "health",
        "Annual eye examination and prescription update",
    ),
    ("Prescription medication refill", "health", "Monthly blood pressure medication"),
    ("Massage therapy session", "health", "60 minute deep tissue sports massage"),
    ("Yoga class pack", "health", "10-class yoga and pilates pack"),
    ("Running shoes from REI", "health", "Trail running shoes for marathon training"),
    (
        "Protein powder and shaker",
        "health",
        "Whey protein powder for post workout recovery",
    ),
    # utilities
    ("Electric bill monthly", "utilities", "Monthly electricity usage home"),
    ("Gas heating bill", "utilities", "Monthly natural gas heating bill"),
    ("Internet broadband subscription", "utilities", "Monthly fibre broadband plan"),
    ("Mobile phone plan", "utilities", "Monthly unlimited data and calls"),
    ("Water bill quarterly", "utilities", "Quarterly water and sewage charges"),
    (
        "Home insurance premium",
        "utilities",
        "Monthly home contents and building insurance",
    ),
    ("Trash and recycling collection", "utilities", "Monthly waste management service"),
    ("Amazon Prime annual fee", "utilities", "Yearly prime membership renewal"),
    ("iCloud storage subscription", "utilities", "Monthly 200GB iCloud storage plan"),
    ("Adobe Creative Cloud", "utilities", "Monthly creative software subscription"),
    # shopping
    (
        "Amazon order noise cancelling headphones",
        "shopping",
        "Sony WH-1000XM5 headphones for work from home",
    ),
    ("IKEA furniture assembly", "shopping", "Billy bookcase and Kallax shelf unit"),
    ("New winter jacket North Face", "shopping", "Waterproof down insulated jacket"),
    ("Levi 501 jeans purchase", "shopping", "Classic straight fit denim jeans"),
    ("Laptop backpack waterproof", "shopping", "Osprey travel backpack for commuting"),
    ("Wireless earbuds replacement", "shopping", "AirPods Pro second generation"),
    (
        "Desk lamp and office supplies",
        "shopping",
        "LED desk lamp pens notebooks and folders",
    ),
    (
        "Kitchen appliance blender",
        "shopping",
        "Vitamix high speed blender for smoothies",
    ),
    (
        "Bedding sheets and pillows",
        "shopping",
        "Egyptian cotton duvet cover and pillowcases",
    ),
    (
        "Phone case and screen protector",
        "shopping",
        "iPhone protective case and tempered glass",
    ),
    # travel
    (
        "Flight to New York round trip",
        "travel",
        "Economy class round trip ticket to JFK",
    ),
    ("Hotel stay in Chicago", "travel", "3 night stay in downtown boutique hotel"),
    ("Airbnb cabin weekend rental", "travel", "Cozy upstate cabin for weekend escape"),
    ("Car rental road trip", "travel", "SUV rental for 4 day coastal road trip"),
    (
        "Weekend hotel city break",
        "travel",
        "2 night stay in boutique bed and breakfast",
    ),
    ("Travel insurance policy", "travel", "Comprehensive travel and medical insurance"),
    (
        "Luggage and packing cubes",
        "travel",
        "Hardshell carry-on and packing organizers",
    ),
    ("Airport lounge day pass", "travel", "Priority pass lounge access during layover"),
    (
        "Tourist attraction tickets",
        "travel",
        "Empire State Building observation deck tickets",
    ),
    (
        "Currency exchange travel money",
        "travel",
        "Euros and British pounds for European trip",
    ),
    # miscellaneous
    ("Haircut and styling", "other", "Monthly haircut and beard trim at barber"),
    (
        "Dry cleaning suit and shirts",
        "other",
        "Formal suit and three dress shirts cleaned",
    ),
    ("Post office shipping fees", "other", "Parcels shipped to family overseas"),
    ("Online course subscription", "other", "Udemy annual subscription for learning"),
    ("Charity donation monthly", "other", "Monthly donation to local food bank"),
    ("Birthday gift wrapping", "other", "Gift and wrapping paper for friends birthday"),
    (
        "Newspaper digital subscription",
        "other",
        "Monthly New York Times digital access",
    ),
    ("Home repair plumber visit", "other", "Emergency plumber for leaking kitchen tap"),
    ("Pet food and supplies", "other", "Dog food treats and grooming brush"),
    (
        "Stationery and art supplies",
        "other",
        "Sketchbook watercolours and fine liner pens",
    ),
    (
        "Flowers and plant delivery",
        "other",
        "Bouquet of flowers and indoor succulent plant",
    ),
    ("Candles and home fragrance", "other", "Scented soy candles and reed diffuser"),
    ("Sunscreen and skincare", "other", "SPF 50 sunscreen moisturiser and face wash"),
    (
        "Umbrella and rain gear",
        "other",
        "Windproof compact umbrella and waterproof boots",
    ),
    ("Language learning app", "other", "Duolingo Plus annual subscription for Spanish"),
    (
        "Meditation app subscription",
        "other",
        "Headspace annual mindfulness subscription",
    ),
    ("Podcast equipment microphone", "other", "USB condenser microphone for recording"),
    ("Second hand book purchase", "other", "5 paperback novels from used bookstore"),
    (
        "Printer ink cartridges",
        "other",
        "Black and colour ink cartridges for home printer",
    ),
    (
        "Extension cord and adapters",
        "other",
        "Power strip with USB ports and travel adapters",
    ),
]


async def seed():
    now = datetime.now(timezone.utc)
    async with httpx.AsyncClient() as client:
        for i, (title, category, description) in enumerate(TRANSACTIONS, 1):
            days_ago = random.randint(0, 365)
            payload = {
                "title": title,
                "description": description,
                "amount": round(random.uniform(3.0, 600.0), 2),
                "is_expense": True,
                "category": category,
                "date": (
                    now - timedelta(days=days_ago, hours=random.randint(0, 23))
                ).isoformat(),
            }
            response = await client.post(BASE_URL, json=payload)
            response.raise_for_status()
            print(f"[{i}/{len(TRANSACTIONS)}] Created: {title}")

    print(f"\n✅ Seeded {len(TRANSACTIONS)} transactions")


if __name__ == "__main__":
    asyncio.run(seed())
