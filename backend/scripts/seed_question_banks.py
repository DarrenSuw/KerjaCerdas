"""One-time script to seed question banks for common CV skills."""

import asyncio
import logging
import time

from backend.app.api.database import init_db
from backend.app.db import postgres_store as store
from backend.app.services.quiz.generator import BANK_TARGET, ensure_questions_exist

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SKILLS_TO_SEED = [
    # Programming languages
    "Python", "R Programming", "Java", "JavaScript", "TypeScript", "C", "C++", "C#", "Go", "Rust", 
    "Kotlin", "Swift", "PHP", "Ruby", "Scala", "MATLAB", "Bash/Shell Scripting", "Dart", "Lua",

    # Web & frontend
    "HTML", "CSS", "React", "Vue.js", "Angular", "Next.js", "Svelte", "Bootstrap", "Tailwind CSS", 
    "jQuery", "REST API", "GraphQL", "WebSocket",

    # Backend & cloud
    "Node.js", "Django", "FastAPI", "Flask", "Spring Boot", "Laravel", "Express.js", "Docker", 
    "Kubernetes", "AWS", "Google Cloud Platform", "Microsoft Azure", "CI/CD", "Linux", "Nginx",

    # Data & analytics
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Power BI", "Tableau", 
    "Excel (Advanced)", "Google Sheets (Advanced)", "Data Mining", "Business Analytics", 
    "Data Visualization", "ETL", "Apache Spark", "Hadoop", "Airflow",

    # AI & ML
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Scikit-learn", "NLP", 
    "Computer Vision", "Data Science", "Pandas", "NumPy", "Matplotlib", "Seaborn", 
    "Feature Engineering", "Model Deployment",

    # Design & product
    "Figma", "Adobe XD", "UI/UX Design", "Canva", "Adobe Photoshop", "Adobe Illustrator", 
    "Product Management", "Agile/Scrum", "Jira", "Notion",

    # Finance & business
    "Financial Modeling", "Accounting", "Microsoft Word", "Microsoft PowerPoint", 
    "Project Management", "Business Development", "Digital Marketing", "SEO", "Google Analytics", 
    "Social Media Marketing", "Content Writing", "Copywriting",

    # Other technical
    "Cybersecurity", "Network Administration", "Blockchain", "IoT", "Embedded Systems", 
    "AutoCAD", "SAP"
]

async def seed_banks():
    await init_db()
    
    total = len(SKILLS_TO_SEED)
    logger.info(f"Starting seed for {total} skills. Target size per skill: {BANK_TARGET}")
    
    for idx, skill_name in enumerate(SKILLS_TO_SEED, 1):
        try:
            from backend.app.services.matching.evidence import skill_key
            key = skill_key(skill_name)
            
            have = await store.count_active_questions_for_skill(key)
            if have >= BANK_TARGET:
                logger.info(f"[{idx}/{total}] SKIPPED: '{skill_name}' already has {have} questions.")
                continue
                
            logger.info(f"[{idx}/{total}] GENERATING: '{skill_name}' (currently has {have})...")
            added = await ensure_questions_exist(skill_name, target=BANK_TARGET)
            
            if added > 0:
                logger.info(f"[{idx}/{total}] SUCCESS: Added {added} questions to '{skill_name}'.")
                # Sleep between successful generations to respect API rate limits
                await asyncio.sleep(2.5)
            else:
                logger.warning(f"[{idx}/{total}] FAILED: No questions generated for '{skill_name}'.")
                
        except Exception as exc:
            logger.error(f"[{idx}/{total}] ERROR on '{skill_name}': {exc}")
            # Cool down on errors in case it's a rate limit block
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(seed_banks())
