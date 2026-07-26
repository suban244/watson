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
    # groceries
    (
        "Grocery shopping at Whole Foods",
        "groceries",
        "Weekly grocery run, fruits vegetables and dairy",
    ),
    (
        "Late night snacks from 7-Eleven",
        "groceries",
        "Chips crisps and energy drink",
    ),
    (
        "Farmers market fruit and veg",
        "groceries",
        "Seasonal vegetables and fresh strawberries",
    ),
    (
        "Meal prep ingredients",
        "groceries",
        "Chicken breast rice and broccoli for the week",
    ),
    (
        "Bakery croissants and bread",
        "groceries",
        "Sourdough loaf and assorted pastries",
    ),
    # dining_out
    (
        "Coffee at Blue Bottle Coffee",
        "dining_out",
        "Morning espresso and almond croissant",
    ),
    ("Lunch at Chipotle", "dining_out", "Burrito bowl with guacamole and chips"),
    ("Dinner at Nobu restaurant", "dining_out", "Omakase dinner for special occasion"),
    (
        "Pizza delivery from Dominos",
        "dining_out",
        "Large pepperoni pizza and garlic bread",
    ),
    ("Sushi takeout from Sakura", "dining_out", "Friday night sushi and miso soup"),
    ("Brunch at The Egg Shop", "dining_out", "Eggs benedict and fresh orange juice"),
    ("Taco Tuesday street food", "dining_out", "Carne asada tacos from the food cart"),
    (
        "Smoothie bar after gym",
        "dining_out",
        "Protein smoothie with banana and peanut butter",
    ),
    (
        "Starbucks coffee and sandwich",
        "dining_out",
        "Caramel latte and turkey sandwich",
    ),
    (
        "Indian takeout curry night",
        "dining_out",
        "Butter chicken and garlic naan delivery",
    ),
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
    ("Weekly bus pass", "transport", "City bus weekly travel card"),
    ("Electric scooter rental", "transport", "Lime scooter rental downtown"),
    # travel
    ("Train ticket to Boston", "travel", "Amtrak express round trip ticket"),
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
    # experiences
    (
        "Cinema tickets Friday night",
        "experiences",
        "Two tickets for new blockbuster film",
    ),
    ("Steam game purchase", "experiences", "New RPG game on PC platform"),
    (
        "Concert tickets live music",
        "experiences",
        "Rock concert at Madison Square Garden",
    ),
    (
        "Board game night purchase",
        "experiences",
        "Catan and Ticket to Ride expansion packs",
    ),
    (
        "Museum natural history visit",
        "experiences",
        "Family tickets to natural history museum",
    ),
    (
        "Museum annual membership",
        "experiences",
        "Yearly pass to art and science museums",
    ),
    ("Escape room booking", "experiences", "Group escape room experience downtown"),
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
    # education
    ("Kindle ebook bundle", "education", "Three fiction novels downloaded"),
    (
        "Online course subscription",
        "education",
        "Udemy annual subscription for learning",
    ),
    (
        "Language learning app",
        "education",
        "Duolingo Plus annual subscription for Spanish",
    ),
    (
        "Second hand book purchase",
        "education",
        "5 paperback novels from used bookstore",
    ),
    # utilities
    ("Electric bill monthly", "utilities", "Monthly electricity usage home"),
    ("Gas heating bill", "utilities", "Monthly natural gas heating bill"),
    ("Internet broadband subscription", "utilities", "Monthly fibre broadband plan"),
    ("Mobile phone plan", "utilities", "Monthly unlimited data and calls"),
    ("Water bill quarterly", "utilities", "Quarterly water and sewage charges"),
    ("Trash and recycling collection", "utilities", "Monthly waste management service"),
    # subscriptions
    (
        "Netflix monthly subscription",
        "subscriptions",
        "Streaming subscription for movies and shows",
    ),
    ("Spotify premium plan", "subscriptions", "Monthly music and podcast streaming"),
    ("Amazon Prime annual fee", "subscriptions", "Yearly prime membership renewal"),
    (
        "iCloud storage subscription",
        "subscriptions",
        "Monthly 200GB iCloud storage plan",
    ),
    ("Adobe Creative Cloud", "subscriptions", "Monthly creative software subscription"),
    (
        "Newspaper digital subscription",
        "subscriptions",
        "Monthly New York Times digital access",
    ),
    (
        "Meditation app subscription",
        "subscriptions",
        "Headspace annual mindfulness subscription",
    ),
    # household
    (
        "Home insurance premium",
        "household",
        "Monthly home contents and building insurance",
    ),
    ("IKEA furniture assembly", "household", "Billy bookcase and Kallax shelf unit"),
    (
        "Desk lamp and office supplies",
        "household",
        "LED desk lamp pens notebooks and folders",
    ),
    (
        "Kitchen appliance blender",
        "household",
        "Vitamix high speed blender for smoothies",
    ),
    (
        "Bedding sheets and pillows",
        "household",
        "Egyptian cotton duvet cover and pillowcases",
    ),
    (
        "Home repair plumber visit",
        "household",
        "Emergency plumber for leaking kitchen tap",
    ),
    (
        "Flowers and plant delivery",
        "household",
        "Bouquet of flowers and indoor succulent plant",
    ),
    (
        "Candles and home fragrance",
        "household",
        "Scented soy candles and reed diffuser",
    ),
    (
        "Printer ink cartridges",
        "household",
        "Black and colour ink cartridges for home printer",
    ),
    (
        "Extension cord and adapters",
        "household",
        "Power strip with USB ports and travel adapters",
    ),
    # personal_items
    (
        "Amazon order noise cancelling headphones",
        "personal_items",
        "Sony WH-1000XM5 headphones for work from home",
    ),
    (
        "New winter jacket North Face",
        "personal_items",
        "Waterproof down insulated jacket",
    ),
    ("Levi 501 jeans purchase", "personal_items", "Classic straight fit denim jeans"),
    (
        "Laptop backpack waterproof",
        "personal_items",
        "Osprey travel backpack for commuting",
    ),
    ("Wireless earbuds replacement", "personal_items", "AirPods Pro second generation"),
    (
        "Phone case and screen protector",
        "personal_items",
        "iPhone protective case and tempered glass",
    ),
    (
        "Haircut and styling",
        "personal_items",
        "Monthly haircut and beard trim at barber",
    ),
    (
        "Dry cleaning suit and shirts",
        "personal_items",
        "Formal suit and three dress shirts cleaned",
    ),
    (
        "Stationery and art supplies",
        "personal_items",
        "Sketchbook watercolours and fine liner pens",
    ),
    (
        "Sunscreen and skincare",
        "personal_items",
        "SPF 50 sunscreen moisturiser and face wash",
    ),
    (
        "Umbrella and rain gear",
        "personal_items",
        "Windproof compact umbrella and waterproof boots",
    ),
    (
        "Podcast equipment microphone",
        "personal_items",
        "USB condenser microphone for recording",
    ),
    # gifts
    (
        "Birthday gift wrapping",
        "gifts",
        "Gift and wrapping paper for friends birthday",
    ),
    # misc
    ("Post office shipping fees", "misc", "Parcels shipped to family overseas"),
    ("Charity donation monthly", "misc", "Monthly donation to local food bank"),
    ("Pet food and supplies", "misc", "Dog food treats and grooming brush"),
]


async def seed():
    now = datetime.now(timezone.utc)
    async with httpx.AsyncClient() as client:
        for i, (title, category, description) in enumerate(TRANSACTIONS, 1):
            days_ago = random.randint(0, 30)
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
