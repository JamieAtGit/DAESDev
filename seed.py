from marketplace.models import (
    CustomUser, ProducerProfile, Category, Product,
    SurplusProduce, CommunityPost
)
from datetime import date, timedelta
from django.utils import timezone

# ── Categories ──────────────────────────────────────────────────────────────
veg     = Category.objects.get_or_create(name='Vegetables',    slug='vegetables')[0]
dairy   = Category.objects.get_or_create(name='Dairy & Eggs',  slug='dairy-eggs')[0]
bakery  = Category.objects.get_or_create(name='Bakery',        slug='bakery')[0]
preserves = Category.objects.get_or_create(name='Preserves',   slug='preserves')[0]
seasonal  = Category.objects.get_or_create(name='Seasonal Specialities', slug='seasonal')[0]

# ── Producer 1 — John's Farm (BS48) ─────────────────────────────────────────
u1 = CustomUser.objects.create_user(
    username='farmer_john', password='pass1234', role='producer',
    phone='01179 100001'
)
p1 = ProducerProfile.objects.create(
    user=u1, business_name="John's Farm",
    address="1 Farm Lane, Nailsea", postcode="BS48 3DF",
    description="Family-run mixed farm producing seasonal vegetables and free-range eggs since 1987."
)
Product.objects.create(producer=p1, category=veg,    name='Organic Carrots',     description='Sweet Chantenay carrots, freshly harvested.',          price=1.50, stock=100, allergens='None',          is_organic=True,  harvest_date=date.today(),                  farm_origin="John's Farm, Nailsea",    lead_time_hours=48, is_seasonal=True,  seasonal_months='September – March')
Product.objects.create(producer=p1, category=veg,    name='Organic Potatoes',    description='White Maris Piper, great for roasting or mash.',       price=2.00, stock=80,  allergens='None',          is_organic=True,  harvest_date=date.today(),                  farm_origin="John's Farm, Nailsea",    lead_time_hours=48, is_seasonal=False)
Product.objects.create(producer=p1, category=veg,    name='Organic Leeks',       description='Tender leeks, freshly pulled.',                        price=1.80, stock=60,  allergens='None',          is_organic=True,  harvest_date=date.today(),                  farm_origin="John's Farm, Nailsea",    lead_time_hours=48, is_seasonal=True,  seasonal_months='October – February')
Product.objects.create(producer=p1, category=dairy,  name='Free Range Eggs',     description='12 large eggs from our free-range hens.',              price=3.20, stock=50,  allergens='Eggs',          is_organic=False, farm_origin="John's Farm, Nailsea",    lead_time_hours=48)
Product.objects.create(producer=p1, category=bakery, name='Sourdough Loaf',      description='Stone baked sourdough, 800g.',                         price=4.00, stock=20,  allergens='Gluten, Wheat', is_organic=False, farm_origin="John's Farm, Nailsea",    lead_time_hours=24)

# Community posts for p1
CommunityPost.objects.create(producer=p1, post_type='story',   title='How we started farming organically', content='Back in 2003 we made the decision to convert our land to organic production. It took three years to gain certification but the results speak for themselves — better soil, healthier animals, and customers who keep coming back.')
CommunityPost.objects.create(producer=p1, post_type='recipe',  title='Roasted Carrot and Leek Soup',       content='Roast 500g carrots and 2 leeks with olive oil at 200°C for 25 minutes. Blend with 1 litre of vegetable stock, season well. Serve with a slice of our sourdough. Simple, seasonal, and warming.')
CommunityPost.objects.create(producer=p1, post_type='storage', title='Storing root vegetables',            content='Keep carrots and potatoes in a cool, dark place — ideally a paper bag in a larder. Avoid the fridge for potatoes as the cold converts starch to sugar. Properly stored they will last 2–3 weeks.')

# ── Producer 2 — Hillside Dairy (BS40) ──────────────────────────────────────
u2 = CustomUser.objects.create_user(
    username='hillside_dairy', password='pass1234', role='producer',
    phone='01275 200002'
)
p2 = ProducerProfile.objects.create(
    user=u2, business_name="Hillside Dairy",
    address="Hillside Farm, Chew Valley", postcode="BS40 8SN",
    description="Award-winning dairy farm in the Chew Valley. Supplying fresh milk, cheese and butter to Bristol since 2001."
)
Product.objects.create(producer=p2, category=dairy,    name='Whole Milk (2 litres)',  description='Pasteurised whole milk from our Friesian herd.',       price=1.90, stock=40,  allergens='Milk',              is_organic=False, farm_origin="Hillside Dairy, Chew Valley",  lead_time_hours=24)
Product.objects.create(producer=p2, category=dairy,    name='Mature Cheddar (250g)', description='Aged 12 months, rich and crumbly.',                    price=4.50, stock=30,  allergens='Milk',              is_organic=False, farm_origin="Hillside Dairy, Chew Valley",  lead_time_hours=48)
Product.objects.create(producer=p2, category=dairy,    name='Salted Butter (250g)',  description='Hand-rolled farmhouse butter.',                        price=3.00, stock=25,  allergens='Milk',              is_organic=False, farm_origin="Hillside Dairy, Chew Valley",  lead_time_hours=48)
Product.objects.create(producer=p2, category=dairy,    name='Natural Yoghurt (500g)', description='Live culture yoghurt, no additives.',                 price=2.50, stock=20,  allergens='Milk',              is_organic=True,  farm_origin="Hillside Dairy, Chew Valley",  lead_time_hours=48, is_seasonal=False)
Product.objects.create(producer=p2, category=preserves, name='Chew Valley Honey (340g)', description='Raw wildflower honey harvested from our meadow hives.', price=6.50, stock=15, allergens='None',             is_organic=False, farm_origin="Hillside Dairy, Chew Valley",  lead_time_hours=48)

# Surplus listing for p2
surplus_product = Product.objects.get(producer=p2, name='Whole Milk (2 litres)')
SurplusProduce.objects.create(
    product=surplus_product,
    original_price=1.90, discounted_price=1.30,
    quantity_available=10,
    reason='End of week surplus — perfect condition, must sell by Saturday.',
    available_until=timezone.now() + timedelta(days=3),
)

# Community posts for p2
CommunityPost.objects.create(producer=p2, post_type='story',  title='Life on a Chew Valley dairy farm',   content='We milk 120 Friesian cows twice a day, starting at 5am. The Chew Valley landscape provides rich grazing from April through October which gives our milk its distinctive flavour. We supply Bristol within 24 hours of milking.')
CommunityPost.objects.create(producer=p2, post_type='recipe', title='Simple white sauce with Hillside butter', content='Melt 25g of our salted butter in a pan, stir in 25g plain flour, then gradually whisk in 300ml of our whole milk over a low heat until thick and smooth. Season with nutmeg. Works with pasta, cauliflower cheese, or lasagne.')

# ── Producer 3 — Bristol Valley Bakehouse (BS5) ──────────────────────────────
u3 = CustomUser.objects.create_user(
    username='valley_bakehouse', password='pass1234', role='producer',
    phone='01179 300003'
)
p3 = ProducerProfile.objects.create(
    user=u3, business_name="Bristol Valley Bakehouse",
    address="12 Easton Road, Bristol", postcode="BS5 0EN",
    description="Artisan bakery using heritage grains and long fermentation. All bread baked fresh daily in our Easton bakehouse."
)
Product.objects.create(producer=p3, category=bakery,    name='Seeded Rye Loaf',        description='Dark rye with sunflower and pumpkin seeds, 700g.',    price=4.80, stock=15,  allergens='Gluten, Rye, Seeds', is_organic=False, farm_origin="Bristol Valley Bakehouse", lead_time_hours=24)
Product.objects.create(producer=p3, category=bakery,    name='Cinnamon Spelt Loaf',    description='Lightly spiced spelt loaf, great toasted.',           price=4.20, stock=12,  allergens='Gluten, Wheat',      is_organic=True,  farm_origin="Bristol Valley Bakehouse", lead_time_hours=24)
Product.objects.create(producer=p3, category=bakery,    name='Cheese and Herb Scones (4)', description='Mature cheddar and fresh chive scones.',          price=3.50, stock=18,  allergens='Gluten, Milk, Eggs', is_organic=False, farm_origin="Bristol Valley Bakehouse", lead_time_hours=24)
Product.objects.create(producer=p3, category=preserves, name='Seville Orange Marmalade (340g)', description='Traditional chunky cut marmalade.',           price=4.00, stock=22,  allergens='None',               is_organic=False, farm_origin="Bristol Valley Bakehouse", lead_time_hours=48)
Product.objects.create(producer=p3, category=bakery,    name='Walnut and Date Loaf',   description='Dense, moist loaf. Excellent with cheese.',           price=5.00, stock=10,  allergens='Gluten, Wheat, Nuts', is_organic=False, farm_origin="Bristol Valley Bakehouse", lead_time_hours=24)

# Surplus listing for p3
surplus_product2 = Product.objects.get(producer=p3, name='Cheese and Herb Scones (4)')
SurplusProduce.objects.create(
    product=surplus_product2,
    original_price=3.50, discounted_price=2.45,
    quantity_available=8,
    reason='Baked this morning — perfect condition, best enjoyed today.',
    available_until=timezone.now() + timedelta(hours=10),
)

# Community posts for p3
CommunityPost.objects.create(producer=p3, post_type='story',   title='Why we use heritage grains',          content='Most commercial bread uses modern high-yield wheat varieties bred for volume, not flavour or nutrition. We source heritage spelt and rye from a mill in Somerset. The longer fermentation process (18–24 hours) improves digestibility and gives our bread its distinctive depth of flavour.')
CommunityPost.objects.create(producer=p3, post_type='storage', title='Keeping your sourdough fresh',        content='Store sourdough cut-side down on a wooden board — never in a plastic bag which softens the crust. It will keep well for 3 days. After that, slice and freeze. Toast from frozen for the best results.')

# ── Customers ────────────────────────────────────────────────────────────────
CustomUser.objects.create_user(
    username='sarah_jones', password='pass1234', role='customer',
    phone='07700 100001',
    delivery_address='14 Clifton Road, Bristol',
    delivery_postcode='BS8 1AF'
)
CustomUser.objects.create_user(
    username='robert_johnson', password='pass1234', role='customer',
    phone='07700 100002',
    delivery_address='45 Park Street, Bristol',
    delivery_postcode='BS1 5JG'
)
CustomUser.objects.create_user(
    username='the_clifton_kitchen', password='pass1234', role='restaurant',
    phone='01179 400004',
    delivery_address='22 The Mall, Clifton, Bristol',
    delivery_postcode='BS8 4DR'
)
CustomUser.objects.create_user(
    username='st_marys_school', password='pass1234', role='community_group',
    phone='01179 500005',
    delivery_address='St Mary\'s School, Redland, Bristol',
    delivery_postcode='BS6 6UE'
)

print("Seed complete!")
print("")
print("Producers:  farmer_john / hillside_dairy / valley_bakehouse  (password: pass1234)")
print("Customers:  sarah_jones / robert_johnson                      (password: pass1234)")
print("Restaurant: the_clifton_kitchen                               (password: pass1234)")
print("Community:  st_marys_school                                   (password: pass1234)")
