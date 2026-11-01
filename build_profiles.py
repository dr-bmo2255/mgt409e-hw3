"""Write the customer profiles in profiles/ from CustomerProfile instances.

The profiles are assumed personas for this homework, not researched customer data.
"""

from __future__ import annotations

from config import PROFILES_DIR, PROJECT_DIR, inside_sandbox
from models import CustomerProfile

STUDENT = CustomerProfile(
    profile_id="student",
    label="Yale undergraduate student",
    summary=(
        "A current Yale College undergraduate living in a residential college. Proud of where "
        "they are but wary of looking boastful about it, they wear Yale apparel as everyday "
        "clothing and as a sign of belonging to a college, team, or group. They are quick to "
        "spot marketing that tries too hard."
    ),
    life_stage="18 to 22, full-time student on a limited budget",
    relationship_to_yale="Current undergraduate, member of a residential college and several student groups",
    yale_traditions_valued=[
        "Residential college identity and friendly rivalry between colleges",
        "The Game against Harvard and Bulldog spirit, including Handsome Dan",
        "Academic seriousness and the motto Lux et Veritas, light and truth",
        "Student traditions in the arts: a cappella, theatre, and student publications",
        "A long history worn lightly rather than shown off",
    ],
    yale_modern_values=[
        "Belonging and inclusion across a diverse, international student body",
        "Access: many classmates are on financial aid or are the first in their family at college",
        "Community and service, including being a good neighbour to New Haven",
        "Humility and self-awareness about privilege and elitism",
        "Creative expression and open debate",
        "Sustainability and responsible buying",
    ],
    personal_values=[
        "Authenticity over polish",
        "Friendship and shared experiences",
        "Individual style within a group identity",
    ],
    purchase_role="buys_for_self_and_others",
    buys_for=["themselves", "teammates and club members", "friends and family as occasional gifts"],
    motivations=[
        "Show college, team, or club pride at games and campus events",
        "Wear what friends and teammates are wearing",
        "Own something that looks current, not like a tourist's gift-shop sweatshirt",
    ],
    purchase_occasions=[
        "Move-in and the start of term",
        "The Game and other big home games",
        "Team, club, or residential college orders",
        "Family weekend, when someone else may be paying",
    ],
    decision_drivers=[
        "Seeing friends or other students wearing it",
        "A design specific to their own college, team, or club",
        "A clear price that undercuts or matches the bookstore",
        "A quick mobile checkout",
    ],
    price_sensitivity="high",
    apparel_preferences=[
        "Hoodies and crewnecks in navy or gray",
        "Streetwear fit and styling",
        "College, team, or club designs over plain YALE lettering",
    ],
    media_habits=[
        "Short vertical video on Instagram Reels and TikTok, mostly with sound on",
        "Decides within two seconds whether to keep watching",
        "Shares clips that are funny or clever with friends",
    ],
    cultural_references=[
        "Current hip-hop and pop, and parodies of well-known music videos",
        "Internet humour, memes, and inside jokes about campus life",
        "Classmates appearing on screen rather than models",
    ],
    tone_that_resonates=[
        "Playful, self-aware, and confident without bragging",
        "Made by students, for students",
        "Shows the group, not one hero",
    ],
    call_to_action_needs=[
        "Where to buy, as a link or handle that works on a phone",
        "The price or a student offer",
        "Whether their college or team design exists",
    ],
    turn_offs=[
        "Hard-sell messaging and long voice-overs",
        "Ads that feel made for parents or alumni",
        "Adults imitating student slang",
        "Not being told where to buy or what it costs",
    ],
    appropriateness_concerns=[
        "Flaunting status or wealth, or playing up Ivy League elitism",
        "Stereotypes about any group of students, or a cast that does not look like the student body",
        "Borrowing from a culture or an artist in a way that mocks rather than celebrates",
        "Disrespect toward New Haven or its residents",
    ],
)

PARENT = CustomerProfile(
    profile_id="parent",
    label="Parent of a Yale student",
    summary=(
        "The parent of a current Yale undergraduate, very proud of their child's place at Yale "
        "and of the work and sacrifice behind it. They buy Yale apparel to wear that pride and "
        "as gifts for the family, usually around visits to campus. They want anything carrying "
        "the Yale name to reflect well on the university and on their child."
    ),
    life_stage="45 to 60, established career, paying or helping to pay for college",
    relationship_to_yale="Parent of a current undergraduate; not necessarily a graduate themselves",
    yale_traditions_valued=[
        "Academic excellence and a reputation built since 1701",
        "The motto Lux et Veritas and what a Yale education stands for",
        "The residential college their child belongs to",
        "Ceremony and occasion: move-in, family weekend, The Game, commencement",
        "The Yale name, crest, and classic navy and white",
    ],
    yale_modern_values=[
        "A welcoming, inclusive campus where their child is safe and belongs",
        "Opportunity and access, including for families new to college or on financial aid",
        "Character, service, and leadership alongside academic achievement",
        "Respect for the wider New Haven community",
    ],
    personal_values=[
        "Family pride and supporting their child",
        "Quality and things that last",
        "Good value for money",
        "Dignity and good taste",
    ],
    purchase_role="buys_for_self_and_others",
    buys_for=["themselves", "their student", "siblings, grandparents, and other relatives"],
    motivations=[
        "Show pride in their child, for example with Yale Mom or Yale Dad apparel",
        "Give meaningful gifts to the student and the wider family",
        "Feel part of the Yale community from a distance",
    ],
    purchase_occasions=[
        "Admission and the summer before first year",
        "Move-in day and family weekend",
        "The Game",
        "Holidays, birthdays, and commencement",
    ],
    decision_drivers=[
        "A design that names their role or their child's college",
        "Visible quality of the garment and print",
        "Confidence that the shop is reputable and the product is officially licensed",
        "Easy ordering with delivery in time for the occasion",
    ],
    price_sensitivity="medium",
    apparel_preferences=[
        "Family designs: Yale Mom, Yale Dad, Yale Grandma, Yale Grandpa",
        "Classic crewnecks, quarter-zips, and T-shirts in navy or gray",
        "Clean, traditional lettering and crests",
        "Their child's residential college or team",
    ],
    media_habits=[
        "Facebook, Instagram, email newsletters, and parent group chats",
        "Watches on a phone or laptop, often with the sound off at first",
        "Will watch a full short video if it is about their child's world",
    ],
    cultural_references=[
        "Campus landmarks and scenes of student life",
        "Family moments: drop-off, game day, graduation",
        "Popular music from their own youth more than current hip-hop or internet memes",
    ],
    tone_that_resonates=[
        "Warm, proud, and respectful",
        "Clear and informative about the product",
        "Light humour that includes rather than excludes them",
    ],
    call_to_action_needs=[
        "The shop's name and website",
        "Price, sizes, and delivery time",
        "That family designs exist and how to find them",
    ],
    turn_offs=[
        "References they do not recognise, with no explanation of what is being sold",
        "Fast cuts with no clear view of the product",
        "No sign of who the seller is or whether it can be trusted",
    ],
    appropriateness_concerns=[
        "Aggressive or confrontational tone, profanity, or crude humour attached to the Yale name",
        "Settings or styling that make the university or its students look disreputable",
        "Anything that seems to mock academic seriousness or the families behind the students",
        "Content they would be uncomfortable forwarding to grandparents",
    ],
)


FARMER = CustomerProfile(
    profile_id="farmer",
    label="Middle-aged farmer from Kansas",
    summary=(
        "Runs a family farm in Kansas and has no personal tie to Yale. Knows the name as a "
        "famous East Coast university and would only buy its apparel as a gift, for example "
        "for a relative or a neighbour's child who was admitted. Judges a product by whether "
        "it is well made, fairly priced, and plainly described."
    ),
    life_stage="45 to 60, self-employed, running a family farm",
    relationship_to_yale="None directly; knows Yale by reputation and through news and sport",
    yale_traditions_valued=[
        "A reputation for academic excellence that even people far from it recognise",
        "A long history as one of the country's oldest universities",
        "The achievement it represents when a young person from home gets in",
    ],
    yale_modern_values=[
        "Whether a place like Yale is open to students from rural and working families",
        "Staying down to earth despite its standing",
        "Service to the country and community, not only to its own graduates",
    ],
    personal_values=[
        "Hard work and self-reliance",
        "Family and community",
        "Practicality and plain dealing",
        "Getting fair value for money",
    ],
    purchase_role="buys_for_others",
    buys_for=["a young relative or family friend who was admitted to Yale"],
    motivations=[
        "Mark a young person's achievement with a gift",
        "Little reason to wear a school they have no connection to",
    ],
    purchase_occasions=[
        "A relative's admission or graduation",
        "Christmas and birthdays",
    ],
    decision_drivers=[
        "A garment that looks durable and well made",
        "A clear, fair price",
        "A seller that looks established and trustworthy",
        "Simple ordering and delivery to a rural address",
    ],
    price_sensitivity="high",
    apparel_preferences=[
        "Plain, sturdy sweatshirts and T-shirts",
        "Simple lettering without fashion styling",
        "For themselves, the colours of local teams rather than a distant university",
    ],
    media_habits=[
        "Facebook, YouTube, local television, and radio",
        "Watches on a phone in spare moments, often with the sound off",
        "Gives an unfamiliar ad a few seconds to explain itself",
    ],
    cultural_references=[
        "Country music, college football, and rural life",
        "Unlikely to recognise references to hip-hop music videos or internet memes",
    ],
    tone_that_resonates=[
        "Straightforward and honest about what is for sale",
        "Good-natured humour",
        "Respect for work and family",
    ],
    call_to_action_needs=[
        "What the product is and who it is for",
        "The price",
        "How to order and how long delivery takes",
    ],
    turn_offs=[
        "Stylised imagery with no explanation of what is being sold",
        "Anything that feels aimed only at city or campus insiders",
        "No price or seller information",
    ],
    appropriateness_concerns=[
        "Imagery that comes across as confrontational or intimidating",
        "Any hint of talking down to rural or working people",
        "Profanity or crude humour",
    ],
)

BEIJING_FAMILY = CustomerProfile(
    profile_id="beijing_family",
    label="Family from Beijing touring Yale with their high-school-aged child",
    summary=(
        "Parents and their teenager visiting from Beijing on a tour of American universities. "
        "Yale is a possible future for the student, and the visit matters to the whole family. "
        "They buy apparel as a keepsake of the visit, as encouragement for the student, and as "
        "gifts for relatives and friends at home. English is their second language."
    ),
    life_stage="Parents in their 40s and 50s with a child aged 15 to 17",
    relationship_to_yale="Prospective applicant family on a campus visit; no current tie",
    yale_traditions_valued=[
        "A world-class academic reputation and standing in the Ivy League",
        "More than three centuries of history and a historic campus",
        "Distinguished alumni and faculty",
        "Yale's long-standing links with China",
        "The Yale name and crest as widely recognised symbols",
    ],
    yale_modern_values=[
        "A welcoming community for international students",
        "Student safety and support for those far from home",
        "A global outlook and diverse student body",
        "Research and career opportunities",
    ],
    personal_values=[
        "Education as the family's first priority",
        "The student's effort and achievement",
        "Respect within the family and toward teachers and institutions",
        "Genuine, good-quality goods",
    ],
    purchase_role="buys_for_self_and_others",
    buys_for=["the student", "relatives at home", "the student's classmates and friends"],
    motivations=[
        "A keepsake of the visit that keeps the student's goal in view",
        "Gifts that carry a recognised university name",
        "Sharing the trip with family and friends at home",
    ],
    purchase_occasions=[
        "The day of the campus visit",
        "An admission offer, if it comes",
    ],
    decision_drivers=[
        "Confidence that the merchandise is genuine and officially licensed",
        "Classic designs with the Yale name or crest clearly shown",
        "Good quality that travels well in luggage",
        "A shop that is easy to find near campus and accepts their means of payment",
    ],
    price_sensitivity="medium",
    apparel_preferences=[
        "Classic YALE lettering and crests in navy, gray, or white",
        "Sweatshirts and T-shirts, often several as gifts",
        "Clean, traditional styling over streetwear",
    ],
    media_habits=[
        "WeChat, Xiaohongshu, Douyin, and Bilibili rather than Instagram or TikTok",
        "Relies on visuals and on-screen text more than spoken English",
        "Looks up places to visit and shop before and during the trip",
    ],
    cultural_references=[
        "University rankings and famous campus landmarks",
        "Scenes of student life, libraries, and classrooms",
        "Unlikely to recognise American hip-hop video references or campus in-jokes",
    ],
    tone_that_resonates=[
        "Prestigious, welcoming, and respectful",
        "Clear about what the product is",
        "Shows the campus and the pride of belonging to it",
    ],
    call_to_action_needs=[
        "Where the shop is and when it is open",
        "That the products are official and what they cost",
        "Readable on-screen text; Chinese-language information is a plus",
    ],
    turn_offs=[
        "Slang or cultural references that need explaining",
        "No view of the campus or of what is for sale",
        "Fast cuts that make on-screen details hard to follow",
    ],
    appropriateness_concerns=[
        "Imagery that makes the university or its surroundings look unsafe",
        "A confrontational or unserious tone attached to a university they respect",
        "Anything that seems to belittle study or academic achievement",
    ],
)

URBAN_20 = CustomerProfile(
    profile_id="urban_20",
    label="20-year-old who grew up in a big-city neighbourhood",
    summary=(
        "Grew up in the urban core of a major city such as Los Angeles, Chicago, New York, or "
        "Miami, and is now working, studying locally, or both. Has no tie to Yale and would "
        "wear its apparel as style, not affiliation. Fluent in music, streetwear, and social "
        "video, and quick to notice when a brand borrows that culture without earning it."
    ),
    life_stage="20, early in work or college, living in their home city",
    relationship_to_yale="None directly; knows Yale as a famous and exclusive university",
    yale_traditions_valued=[
        "The name as a recognised symbol of prestige",
        "Classic collegiate lettering as a fashion look",
        "Ivy League standing, viewed with both interest and scepticism",
    ],
    yale_modern_values=[
        "Whether elite universities are really open to people from neighbourhoods like theirs",
        "Representation: seeing people who look and dress like them treated with respect",
        "Honesty about privilege rather than pretending it is not there",
    ],
    personal_values=[
        "Authenticity and being true to where they come from",
        "Loyalty to friends and neighbourhood",
        "Personal style and self-expression",
        "Making their own way",
    ],
    purchase_role="buys_for_self",
    buys_for=["themselves"],
    motivations=[
        "The collegiate streetwear look",
        "Wearing what artists, athletes, and people they respect are wearing",
        "A sense of aspiration, on their own terms",
    ],
    purchase_occasions=[
        "Seeing a piece in a video or on someone whose style they rate",
        "A new release or limited run",
        "Payday or back-to-school season",
    ],
    decision_drivers=[
        "Fit, weight, and how the garment looks worn",
        "Credibility: who is wearing it and whether the brand feels real",
        "Price against the streetwear and sportswear brands they already buy",
        "A link that goes straight to the product",
    ],
    price_sensitivity="medium",
    apparel_preferences=[
        "Heavyweight, roomy hoodies and crewnecks",
        "Bold collegiate lettering in navy, black, or gray",
        "Pieces that work with sneakers and everyday streetwear",
    ],
    media_habits=[
        "TikTok, Instagram, and YouTube, with sound on",
        "Watches music videos and creators closely and shares what stands out",
        "Scrolls past anything that looks like a conventional advert",
    ],
    cultural_references=[
        "Hip-hop past and present, including well-known music videos",
        "Sneaker and streetwear culture",
        "Pride in their own city",
    ],
    tone_that_resonates=[
        "Confident, stylish, and unforced",
        "Led by music and visuals rather than a sales pitch",
        "Made with the culture, not about it",
    ],
    call_to_action_needs=[
        "Where to buy, as a direct link or handle",
        "Price, sizing, and fit",
        "Whether it ships to them",
    ],
    turn_offs=[
        "Awkward imitation of music videos or street style",
        "Preppy or exclusive messaging",
        "No way to find or buy the item shown",
    ],
    appropriateness_concerns=[
        "An elite institution using urban settings or hip-hop imagery as a costume",
        "City life shown as a caricature, or people used as background props",
        "Mocking the artists or communities a style comes from",
    ],
)

ALL_PROFILES = (STUDENT, PARENT, FARMER, BEIJING_FAMILY, URBAN_20)


def main() -> None:
    PROFILES_DIR.mkdir(exist_ok=True)
    for profile in ALL_PROFILES:
        path = inside_sandbox(PROFILES_DIR / f"profile_{profile.profile_id}.json", PROFILES_DIR)
        path.write_text(profile.model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {path.relative_to(PROJECT_DIR).as_posix()}")


if __name__ == "__main__":
    main()
