import random
from db_setup import Session, User, init_db

# Names from the seed_mock.sql
names_profiles = [
    ('Aymen Ben Salah','student'),
    ('Sarah Trabelsi','student'),
    ('Youssef Kallel','student'),
    ('Mariem Gharbi','researcher'),
    ('Rim Ayadi','student'),
    ('Hedi Mansouri','student'),
    ('Ines Bouazizi','student'),
    ('Walid Jaziri','student'),
    ('Khalil Zouari','student'),
    ('Amira Ben Amor','student'),
    ('Omar Ben Youssef','student'),
    ('Salma Ktari','student'),
    ('Nour Ghedira','student'),
    ('Hamza Feki','student'),
    ('Fatma Louati','student'),
    ('Karim Chebbi','student'),
    ('Sonia Mejri','student'),
    ('Mehdi Chatti','student'),
    ('Dhia Eddine','student'),
    ('Sarra Abid','student'),
    ('Ahmed Ben Ali','student'),
    ('Rania Khemiri','student'),
    ('Bilel Toumi','student'),
    ('Mouna Jlassi','student'),
    ('Skander Triki','student'),
    ('Yasmine Saidi','student'),
    ('Houssem Ayari','student'),
    ('Asma Ghannouchi','student'),
    ('Tarek Kallel','student'),
    ('Chaima Ben Salem','student'),
    ('Nader Baccar','student'),
    ('Imen Dridi','student'),
    ('Lotfi Hajri','student'),
    ('Zied Hammami','student')
]

all_skills = [
    'Python', 'SQL', 'Machine Learning', 'Deep Learning', 
    'Data Engineering', 'NLP', 'Power BI', 'React', 
    'Node.js', 'Embedded C', 'STM32', 'Linux'
]

all_interests = [
    'AI', 'Data Science', 'Software Engineering', 
    'Embedded Systems', 'Web Development', 'Cloud'
]

def seed_users():
    session = Session()
    
    # Optional: Clear existing users before seeding to prevent duplicates if run multiple times
    session.query(User).delete()
    
    for name, profile in names_profiles:
        # Give them 2 to 5 random skills
        user_skills = random.sample(all_skills, k=random.randint(2, 5))
        
        # Give them 1 to 3 random interests
        user_interests = random.sample(all_interests, k=random.randint(1, 3))
        
        user = User(
            name=name,
            profile=profile,
            skills=", ".join(user_skills),
            interests=", ".join(user_interests)
        )
        session.add(user)
    
    session.commit()
    count = session.query(User).count()
    session.close()
    print(f"Successfully seeded {count} fake Tunisian students into the database.")

if __name__ == "__main__":
    # Ensure DB is initialized
    init_db()
    seed_users()
