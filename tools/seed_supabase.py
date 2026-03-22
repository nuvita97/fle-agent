#!/usr/bin/env python3
"""
One-time migration script: seed Supabase with existing content.

Seeds:
  1. fun_facts  — from the 50 hardcoded cultural facts (5 original topics)
  2. exercises  — from the 25 JSON files in cache/ (5 levels × 5 topics)

New topics (sante_bien_etre, education_apprentissage) have no JSON files yet
and will be skipped gracefully — their content will be built by prebuild_cache.py.

Usage:
    python tools/seed_supabase.py              # safe to re-run (upsert)
    python tools/seed_supabase.py --force      # delete + re-insert fun_facts
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Fun facts — copied from app.py CULTURAL_FACTS (50 facts, 5 original topics)
# ---------------------------------------------------------------------------
CULTURAL_FACTS = {
    "vie_quotidienne": [
        "En France, le déjeuner est souvent considéré comme le repas principal de la journée et peut durer plus d'une heure, même en semaine !",
        "Les Français consomment en moyenne 26 kg de fromage par personne et par an — le record mondial. Il existerait plus de 1 200 variétés de fromages français !",
        "La bise (se faire la bise) est une salutation courante en France, mais le nombre de bises varie selon les régions : 1 en Bretagne, 2 à Paris, jusqu'à 4 dans certaines régions du Sud.",
        "En France, les pharmacies sont identifiées par une croix verte lumineuse. Elles jouent un rôle important dans le système de santé : les pharmaciens peuvent donner des conseils médicaux de base.",
        "Le marché du dimanche est une tradition profondément ancrée dans la culture française. Même dans les petits villages, un marché hebdomadaire rassemble producteurs locaux et habitants.",
        "La France compte 11 jours fériés nationaux par an, dont le 14 juillet (Fête Nationale) qui commémore la prise de la Bastille en 1789.",
        "Les Français sont parmi les plus grands consommateurs de pain au monde : une baguette fraîche par jour et par foyer en moyenne !",
        "Le mot « café » désigne à la fois la boisson et le lieu. Un simple café au comptoir coûte généralement moins cher qu'une table en terrasse — une particularité typiquement française.",
        "En France, les enfants ont généralement deux heures de pause déjeuner à l'école, une tradition qui valorise le repas comme moment social important.",
        "La pétanque, jeu de boules très populaire, se joue dans presque tous les villages français. Elle est souvent associée à la convivialité du Sud de la France.",
    ],
    "voyages_tourisme": [
        "La France est le pays le plus visité au monde, accueillant plus de 89 millions de touristes chaque année. Paris seule reçoit plus de visiteurs que toute l'Australie !",
        "Le Mont-Saint-Michel, une abbaye perchée sur un rocher en Normandie, accueille environ 3 millions de visiteurs par an et est entouré par les marées deux fois par jour.",
        "La France possède 53 sites classés au patrimoine mondial de l'UNESCO — des châteaux de la Loire aux gorges du Verdon en passant par les arènes de Nîmes.",
        "Le Tour de France, la plus célèbre course cycliste au monde, traverse chaque été des dizaines de régions françaises et attire des millions de spectateurs sur le bord des routes.",
        "La Côte d'Azur (French Riviera) a été popularisée par des artistes comme Picasso et Matisse au début du XXe siècle. Elle reste l'une des destinations balnéaires les plus prisées d'Europe.",
        "Le château de Versailles, résidence royale construite par Louis XIV, possède 2 300 pièces et des jardins s'étendant sur 800 hectares. Il faudrait plusieurs jours pour tout visiter !",
        "La France est traversée par plus de 185 000 km de routes et chemins de randonnée, dont le célèbre GR 20 en Corse, considéré comme l'un des sentiers les plus difficiles d'Europe.",
        "Chaque année, des millions de pèlerins marchent le Chemin de Saint-Jacques-de-Compostelle qui traverse la France du Nord jusqu'aux Pyrénées, souvent plus de 1 500 km à pied.",
        "La ville de Lyon est classée au patrimoine mondial de l'UNESCO pour son ensemble architectural exceptionnel. Elle est aussi considérée comme la capitale mondiale de la gastronomie.",
        "Le viaduc de Millau, inauguré en 2004, est le pont routier le plus haut du monde avec un pilier culminant à 343 mètres — plus haut que la Tour Eiffel !",
    ],
    "environnement_ecologie": [
        "La France s'est engagée à atteindre la neutralité carbone d'ici 2050. Le pays possède déjà l'un des réseaux de transport ferroviaire à grande vitesse les plus étendus d'Europe.",
        "La forêt couvre environ 31 % du territoire français, soit 17 millions d'hectares. Cette superficie a doublé en moins de deux siècles grâce aux politiques de reboisement.",
        "La France produit environ 70 % de son électricité à partir du nucléaire, ce qui lui permet d'avoir l'un des taux d'émissions de CO₂ par habitant les plus bas d'Europe.",
        "Les Alpes françaises abritent le Mont-Blanc (4 808 m), le plus haut sommet d'Europe occidentale. Les glaciers alpins reculent cependant de plusieurs mètres chaque année à cause du réchauffement climatique.",
        "La Camargue, dans le delta du Rhône, est l'une des plus grandes zones humides d'Europe. Elle abrite des flamants roses sauvages et des chevaux blancs semi-sauvages emblématiques.",
        "La France compte 11 parcs nationaux qui protègent ses écosystèmes les plus fragiles, des Pyrénées aux Calanques de Marseille en passant par le parc des Écrins dans les Alpes.",
        "En France, la loi « anti-gaspillage » de 2020 interdit la destruction des invendus non alimentaires et oblige les grandes surfaces à donner leurs invendus alimentaires à des associations.",
        "La France abrite plus de 40 000 espèces animales et végétales. La biodiversité marine de l'Outre-mer français est parmi les plus riches du monde, notamment en Polynésie française.",
        "Les zones marines protégées françaises s'étendent sur plus de 23 % des eaux sous juridiction française, avec des objectifs d'atteindre 30 % d'ici 2030.",
        "Chaque année, le label « Vignobles & Découvertes » encourage un tourisme responsable dans les régions viticoles françaises, promouvant des pratiques agricoles durables et biologiques.",
    ],
    "technologie_numerique": [
        "La France est l'un des leaders mondiaux en intelligence artificielle, avec des startups comme Mistral AI. Paris est surnommée la « Station F », le plus grand campus de startups au monde.",
        "Le Minitel, ancêtre d'internet créé en France dans les années 1980, a été utilisé par des millions de Français pour consulter des informations et faire des réservations bien avant le World Wide Web.",
        "La France est le berceau du langage de programmation Caml/OCaml, toujours utilisé dans les universités du monde entier pour enseigner la programmation fonctionnelle.",
        "Criteo, BlaBlaCar, Deezer, Dailymotion et Doctolib sont parmi les licornes technologiques françaises les plus connues, faisant de la France un acteur majeur de l'écosystème tech européen.",
        "L'Inria (Institut national de recherche en informatique et en automatique) est l'un des centres de recherche en informatique les plus influents au monde, fondé en France en 1967.",
        "La France a été pionnière dans le déploiement de la 5G en Europe. En 2020, elle a lancé un plan de 100 milliards d'euros pour la relance économique, dont une part importante dédiée au numérique.",
        "Le jeu vidéo est une industrie majeure en France : Ubisoft, Gameloft et Focus Entertainment sont parmi les plus grands studios au monde, créant des franchises comme Assassin's Creed.",
        "La carte à puce (smart card) a été inventée par le Français Roland Moreno en 1974. Cette technologie est aujourd'hui utilisée dans des milliards de cartes bancaires et téléphoniques dans le monde.",
        "En France, le programme « French Tech » regroupe plus de 130 startups labellisées « licornes » ou « futures licornes », avec des levées de fonds record ces dernières années.",
        "La France investit massivement dans la cybersécurité : l'ANSSI (Agence nationale de la sécurité des systèmes d'information) est l'une des agences gouvernementales de cybersécurité les plus reconnues en Europe.",
    ],
    "culture_histoire": [
        "Le Louvre est le musée le plus visité au monde avec 9 millions de visiteurs par an. La Joconde (Mona Lisa) mesure seulement 77 × 53 cm — bien plus petite que la plupart des visiteurs ne l'imaginent !",
        "La Révolution française de 1789 a donné naissance à la devise nationale « Liberté, Égalité, Fraternité » et a inspiré des mouvements démocratiques dans le monde entier.",
        "La Tour Eiffel, construite en 1889 pour l'Exposition universelle, était initialement prévue pour être démolie. Elle est aujourd'hui le monument payant le plus visité au monde avec 7 millions de visiteurs par an.",
        "La langue française est parlée sur les 5 continents par environ 300 millions de personnes. C'est la 5e langue la plus parlée au monde et la 2e la plus étudiée.",
        "La France compte 20 lauréats du prix Nobel de littérature, le plus grand nombre pour un seul pays dans cette catégorie.",
        "Le cinéma a été inventé par les frères Lumière à Lyon en 1895. La France reste l'un des pays avec la plus grande production cinématographique d'Europe, et Cannes accueille le festival le plus prestigieux du monde.",
        "La bande dessinée (BD) est considérée comme le « 9e art » en France. Astérix, Tintin et Lucky Luke sont des personnages emblématiques traduits en plus de 100 langues.",
        "Versailles, la cathédrale Notre-Dame de Paris et le château de Chambord sont parmi les 45 000 monuments historiques protégés en France — le plus grand nombre en Europe.",
        "La gastronomie française a été inscrite au patrimoine culturel immatériel de l'UNESCO en 2010. Le repas gastronomique à la française est reconnu comme une pratique sociale et culturelle unique.",
        "Napoleon Bonaparte a codifié les lois françaises dans le « Code Napoléon » en 1804. Ce code juridique a influencé les systèmes légaux de plus de 40 pays dans le monde.",
    ],
}

LEVELS = ["A1", "A2", "B1", "B2", "C1"]
TOPICS = [
    "vie_quotidienne",
    "sante_bien_etre",
    "education_apprentissage",
    "voyages_tourisme",
    "environnement_ecologie",
    "technologie_numerique",
    "culture_histoire",
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache")


def get_supabase():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)
    return create_client(url, key)


def seed_fun_facts(sb, force: bool = False) -> None:
    if force:
        print("  Deleting existing fun_facts rows...")
        sb.table("fun_facts").delete().neq("id", 0).execute()

    rows = [
        {"topic": topic, "fact": fact}
        for topic, facts in CULTURAL_FACTS.items()
        for fact in facts
    ]
    sb.table("fun_facts").insert(rows).execute()
    print(f"  Inserted {len(rows)} fun_facts rows across {len(CULTURAL_FACTS)} topics.")


def seed_exercises(sb) -> list:
    failed = []
    succeeded = 0
    skipped = 0

    for level in LEVELS:
        for topic in TOPICS:
            path = os.path.join(CACHE_DIR, f"{level}_{topic}.json")
            if not os.path.exists(path):
                print(f"  [SKIP]  {level}/{topic} — no cache file found")
                skipped += 1
                continue

            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            row = {
                "level":      level,
                "topic":      topic,
                "text":       data["text"],
                "url":        data.get("url", ""),
                "site_name":  data.get("site_name", ""),
                "word_count": data.get("word_count", 0),
                "questions":  data.get("questions", []),
                "vocabulary": data.get("vocabulary", []),
            }

            try:
                sb.table("exercises").upsert(row, on_conflict="level,topic").execute()
                print(f"  [OK]    {level}/{topic}")
                succeeded += 1
            except Exception as e:
                print(f"  [FAIL]  {level}/{topic}: {e}")
                failed.append((level, topic))

    print(f"\n  exercises: {succeeded} upserted, {skipped} skipped, {len(failed)} failed")
    return failed


def main():
    parser = argparse.ArgumentParser(description="Seed Supabase with FLE content")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing fun_facts before inserting (exercises always use upsert)",
    )
    args = parser.parse_args()

    sb = get_supabase()

    print("\n=== Seeding fun_facts ===")
    seed_fun_facts(sb, force=args.force)

    print("\n=== Seeding exercises ===")
    failed = seed_exercises(sb)

    if failed:
        print(f"\n⚠ {len(failed)} exercise(s) failed to seed:")
        for level, topic in failed:
            print(f"  - {level}/{topic}")
        sys.exit(1)

    print("\n✓ Seeding complete.")


if __name__ == "__main__":
    main()
