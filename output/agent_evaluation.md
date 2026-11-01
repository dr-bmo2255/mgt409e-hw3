# Agent evaluation

## Part 1 — product identification

Run at 2026-10-04T05:06:50Z with `gpt-6-astra` by `evaluate.py`. The agent was given only the pixels of each photo. The "actual" column comes from the word "true" or "false" in the file name, which was read after the agent had answered.

### Results: agent vs actual

| Photo | Actual | Agent | Verdict | Product identified | Result | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| `image_01_true.jpeg` | yes | yes | match, high confidence | `yale-dad-t-shirt` | Correct | $0.1422 |
| `image_02_false.jpeg` | no | no | no match, high confidence | none | Correct | $0.0312 |
| `image_03_true.jpeg` | yes | yes | match, high confidence | `dry-zone-long-sleeve` | Correct | $0.1492 |
| `image_04_false.jpeg` | no | no | no match, high confidence | none | Correct | $0.0347 |

**4 of 4 correct.** Total cost $0.3573.

### Limits of this test

- The file names say only whether a Campus Customs product is present, not which one.
- Four photos is a small sample. It has no Yale garment that is absent from the catalogue, no colour variant, and no pair of products the agent could not separate, so the `possible_match` paths were not exercised.

### Photo by photo, with the user's commentary

Commentary was entered by the user in the review form (`review_app.py`). 4 of 4 photos reviewed.

#### `image_01_true.jpeg`

- **Actual:** product present · **Agent:** match (high confidence) · **Correct**
- **What the agent saw:** Heather gray short-sleeve T-shirt with navy YALE lettering, horizontal rules, and smaller UNIVERSITY and DAD text on the chest.
- **Steps it took:**
  1. `search_catalogue` — Shortlisted by catalogue fields: yale-dad-t-shirt (score 21), yale-dad-crewneck (score 16), yale-dad-hoodie (score 14), 2025-yale-vs-harvard-t-shirt (score 11), district-tri-blend-t-shirt-vintage-shield (score 11)
  2. `view_catalogue_images` — Opened 1 catalogue reference photo(s) to compare: yale-dad-t-shirt
  3. `add_to_cart` — Added to the shopping cart. No purchase was made.
- **Its reasons:** Reference photo matches the heather gray short-sleeve T-shirt. Navy serif YALE, horizontal rules, and smaller right-aligned UNIVERSITY and DAD match the design.
- **Sidebar:** Yale Dad T-Shirt (`yale-dad-t-shirt`), added to the cart.

**User commentary** (submitted 2026-10-04T05:14:36Z)

*What did the agent do well?*

> Agent was able to drill down in the catalogue based on established criteria of words on the shirt, garment type, sleeve length, color, graphic placement, closure type, affiliation type.  It immediately narrowed it down to 5 items.  Appropriately opened catalogue image and added to cart for me.

*What was bad, or weaker than you would want?*

> Cost of this search was still $0.14.  Performed repeatedly, this could get expensive.

*Were there any mistakes? Describe them.*

> No mistakes

*If there were mistakes, how would you try to fix them?*

> No mistakes, but next iteration, I would like to find a way to get less expensive.

#### `image_02_false.jpeg`

- **Actual:** no product · **Agent:** no match (high confidence) · **Correct**
- **What the agent saw:** Gray pullover hoodie with black ESSENTIALS lettering across the chest.
- **Steps it took:** answered from the photo alone; no catalogue search.
- **Its reasons:** The hoodie reads ESSENTIALS, not Yale. No Yale wording or graphics are visible.
- **Sidebar:** Item is not carried by Campus Customs.

**User commentary** (submitted 2026-10-04T05:16:17Z)

*What did the agent do well?*

> Knew immediately that this was not a catalogue item.  from the text on the shirt.  Cost was $0.0312

*What was bad, or weaker than you would want?*

> Nothing was bad about this.

*Were there any mistakes? Describe them.*

> There were no mistakes

*If there were mistakes, how would you try to fix them?*

> Nothing to fix.

#### `image_03_true.jpeg`

- **Actual:** product present · **Agent:** match (high confidence) · **Correct**
- **What the agent saw:** Navy long-sleeve crewneck tee with large white YALE lettering and smaller BULLDOGS centered beneath.
- **Steps it took:**
  1. `search_catalogue` — Shortlisted by catalogue fields: dry-zone-long-sleeve (score 15), ua-mens-tech-l-s-2-0 (score 15), yale-maplehouse-diana-mockneck (score 10), big-yale-tri-blend-t-shirt (score 9), district-tri-blend-t-shirt-vintage-shield (score 9)
  2. `view_catalogue_images` — Opened 2 catalogue reference photo(s) to compare: dry-zone-long-sleeve, ua-mens-tech-l-s-2-0
  3. `add_to_cart` — Added to the shopping cart. No purchase was made.
- **Its reasons:** Reference photo matches the navy colour and long-sleeve crewneck cut. Solid white serif YALE above smaller BULLDOGS matches the chest design.
- **Sidebar:** Yale Dry-Zone Long-Sleeve Tee (`dry-zone-long-sleeve`), added to the cart.

**User commentary** (submitted 2026-10-04T05:19:01Z)

*What did the agent do well?*

> It inferred the text that cannot be seen.  Letter A in YALE and everything after BU is not seen in BULLDOGS.  
> Narrowed down to 2 items and then compared the image directly.

*What was bad, or weaker than you would want?*

> Again a little costly at $0.15.  I would really like to get that cost down to under $0.03.

*Were there any mistakes? Describe them.*

> no mistakes

*If there were mistakes, how would you try to fix them?*

> no mistakes.  Work on token efficiency.

#### `image_04_false.jpeg`

- **Actual:** no product · **Agent:** no match (high confidence) · **Correct**
- **What the agent saw:** A blue short-sleeve T-shirt with a small white Balenciaga wordmark and red-and-white curved stripes on the chest.
- **Steps it took:** answered from the photo alone; no catalogue search.
- **Its reasons:** The T-shirt displays Balenciaga branding, not Yale wording or graphics. No Yale apparel is visible.
- **Sidebar:** Item is not carried by Campus Customs.

**User commentary** (submitted 2026-10-04T05:20:26Z)

*What did the agent do well?*

> Knew immediately that this was not a Yale shirt

*What was bad, or weaker than you would want?*

> No concerns.  Cost was $0.0347

*Were there any mistakes? Describe them.*

> No mistakes

*If there were mistakes, how would you try to fix them?*

> No mistakes to fix

## Part 2 — ad effectiveness runs

The agent judged `data/videos/ad_humble.mp4` for 5 customer profiles with `gpt-6-astra`. It saw 12 still frames of the ad and could not hear the audio. Both scores run from 0 to 10. There is no answer key for these runs; the user's commentary below is the evaluation.

### Results by profile

| Profile | Appropriateness | Effectiveness | Verdict | Confidence | Cost |
| --- | --- | --- | --- | --- | --- |
| Yale undergraduate student (`student`) | 8 | 5 | mixed | medium | $0.1250 |
| Parent of a Yale student (`parent`) | 6 | 3 | ineffective | medium | $0.1235 |
| Middle-aged farmer from Kansas (`farmer`) | 6 | 2 | ineffective | high | $0.1192 |
| Family from Beijing touring Yale with their high-school-aged child (`beijing_family`) | 6 | 3 | ineffective | high | $0.1241 |
| 20-year-old who grew up in a big-city neighbourhood (`urban_20`) | 6 | 6 | mixed | medium | $0.1239 |

Catalogue item identified in the ad: `basic-hoodie-big-yale`.

### Profile by profile, with the user's commentary

Commentary was entered by the user in the review form (`review_app.py`). 5 of 5 runs reviewed.

#### Yale undergraduate student (`profiles/profile_student.json`)

- **Scores:** appropriateness 8 / 10 · effectiveness 5 / 10 (mixed, medium confidence)
- **What the agent saw:** The ad shows a foreground figure wearing a navy YALE pullover hoodie and gesturing toward the camera beneath a concrete overpass, with a group in casual apparel behind them. Shifting close-ups and wider views give it a music-video-style presentation; the last sampled frame still shows the group, without shopping information.
- **Steps it took:**
  1. `read_customer_profile` — Read profile 'student': Yale undergraduate student.
  2. `watch_ad_video` — Viewed 12 frames sampled across 9.1 seconds. Audio could not be assessed.
  - Catalogue items were reused from the earlier identification of this video.
- **Appropriateness reasons:**
  - The casual clothing and unembellished setting do not visibly flaunt wealth or Ivy League prestige, fitting the customer's concern for humility.
  - The group presentation offers a sense of belonging, although the repeated emphasis on one foreground figure is less aligned with their preference for showing the group rather than one hero.
  - Nothing visible mocks a culture or disparages New Haven; the frames alone cannot establish how any artist reference is handled.
- **Fit with this customer:**
  - *Helps:* Prefers navy hoodies and streetwear styling. — The navy YALE pullover is prominent and worn casually with jeans.
  - *Helps:* Decides within two seconds and enjoys music-video references. — Early close-ups and changing camera angles provide an immediate visual hook, though a specific parody cannot be established from the frames.
  - *Hurts:* Values shared experiences and a group rather than one hero. — A group is present, but most sampled shots privilege the same foreground figure rather than shared interaction.
  - *Hurts:* Prefers college, team, or club designs over plain YALE lettering. — The clearest advertised garment has generic YALE lettering; no clearly legible residential-college or club option is presented.
  - *Hurts:* Highly price-sensitive and needs a mobile shopping link and student offer. — No store identifier, phone-friendly destination, price, or student offer appears in the sampled frames.
  - *Hurts:* Primarily watches short vertical videos on Reels and TikTok. — The approximately nine-second duration suits quick viewing, but the wide-format composition is less suited to a vertical phone feed.
- **Recommendations:** Add a phone-readable Campus Customs link or handle and an actual student price or offer to the closing group shot. Give several group members equal focus and show available residential-college, team, or club designs alongside the plain YALE hoodie. Create a vertical cut with a playful campus-specific visual joke in the first two seconds, keeping the casual group setting rather than adding a hard sell.
- **Limitations:** Audio is unavailable, so music, speech, and the tone of any cultural reference cannot be judged. Evenly sampled frames may miss brief text or actions between samples. The frames do not establish that the participants are students or classmates, which matters to this customer's preference for authentic student-made advertising.

**User commentary** (submitted 2026-10-04T06:34:53Z)

*What did the agent do well?*

> notes effectiveness of music video style.   Notes student preference for dark "streetware" hoodies. Notes that the entire group fosters sense of belonging, but focusing on 1 individual as opposed to the entire community is a little off-brand for Yale.

*What was bad, or weaker than you would want?*

> Limitations of taking only still image clips from the video.  Cannot see the rapid cuts associated with a hip-hop music video.  It is unable to get a transcript with the tools available on PortkeyAPIKey.  It is also unable to analyze the music style with the tools given - it is all inferred

*Were there any mistakes? Describe them.*

> No mistakes, so much as limitations of the model built.

*If there were mistakes, how would you try to fix them?*

> I would work harder to provide it transcript through some of the various mechanisms we described earlier in the problem set.  I would try to obtain tools for the agent that can allow it to analyze the music style, not just the transcript.

#### Parent of a Yale student (`profiles/profile_parent.json`)

- **Scores:** appropriateness 6 / 10 · effectiveness 3 / 10 (ineffective, medium confidence)
- **What the agent saw:** The ad shows a foreground figure wearing a navy hoodie with large white YALE lettering beneath a concrete overpass, with a group in dark apparel behind them. Views alternate between close-ups, elevated angles, and wider group shots, ending on the group without a visible shopping message.
- **Steps it took:**
  1. `read_customer_profile` — Read profile 'parent': Parent of a Yale student.
  2. `watch_ad_video` — Viewed 12 frames sampled across 9.1 seconds. Audio could not be assessed.
  - Catalogue items were reused from the earlier identification of this video.
- **Appropriateness reasons:**
  - The classic navy-and-white Yale lettering supports this parent's preference for traditional university branding and visible family pride.
  - The stern expressions, camera-facing poses, and overpass setting may feel off-key for their preferred warm, dignified portrayal of Yale; the frames do not establish disreputable behavior.
  - No visible crude text, mockery of academics or families, or explicit violence conflicts with their concerns about content suitable for grandparents; audio cannot be assessed.
- **Fit with this customer:**
  - *Helps:* Prefers classic navy and white, clean traditional lettering, and apparel that expresses pride in their child. — The prominent navy hoodie with white YALE lettering makes university affiliation immediately recognizable.
  - *Helps:* Often watches with sound off initially and will watch a short video about their child's world. — The nine-second sequence communicates Yale branding visually, though it does not establish a recognizable campus or family occasion.
  - *Hurts:* Responds to warm, proud, respectful messaging and campus or family moments. — Stern camera-facing poses under an overpass offer little connection to family weekend, academic achievement, or belonging as a parent.
  - *Hurts:* Wants family-role or residential-college designs and meaningful gifts for relatives. — The main product is a generic YALE hoodie; no clearly readable family-role design or explanation of family options appears.
  - *Hurts:* Needs a reputable seller, website, price, sizes, and delivery timing. — No visible Campus Customs identification or shopping information tells this parent where to buy or whether a gift will arrive in time.
  - *Hurts:* Values lasting quality and good value for money. — The changing angles display the logo but provide no fabric, construction, print-quality, or price details to support a purchase decision.
- **Recommendations:** Replace some overpass close-ups with a warm campus-visit or family-weekend scene, retaining the clear navy-and-white Yale branding and showing family-role options. Add a phone-readable closing card with Campus Customs' name, website, actual price, size availability, occasion-relevant delivery timing, and a clear route to family designs. Include a steady product close-up and verified material and licensing information to address this parent's quality and seller-trust concerns.
- **Limitations:** Audio is unavailable, so speech, music, and any audible message or profanity cannot be assessed. Evenly sampled frames may miss brief text or actions and cannot establish the precise editing pace. The frames do not establish garment durability, licensing status, prices, sizes, or delivery availability.

**User commentary** (submitted 2026-10-04T06:39:44Z)

*What did the agent do well?*

> correctly identified that this video does not focus on the student's world that they have just entered on move-in weekend.  Parent will buy a product that features pride in their child.  I really like that it made recommendations on how to make the ad more effective for them

*What was bad, or weaker than you would want?*

> I think if it had more still cuts, transcript and music genre info, the appropriateness score would go down

*Were there any mistakes? Describe them.*

> NO mistakes noted

*If there were mistakes, how would you try to fix them?*

> same fixes that could be applied for the student would also fix the parent ad-appropriateness.

#### Middle-aged farmer from Kansas (`profiles/profile_farmer.json`)

- **Scores:** appropriateness 6 / 10 · effectiveness 2 / 10 (ineffective, high confidence)
- **What the agent saw:** The ad shows a foreground figure wearing a navy hoodie with large white YALE lettering beneath a concrete overpass, with a group in dark collegiate apparel behind. The sampled sequence alternates close, elevated, and wider views and ends on the group, without visible seller information, pricing, or ordering instructions.
- **Steps it took:**
  1. `read_customer_profile` — Read profile 'farmer': Middle-aged farmer from Kansas.
  2. `watch_ad_video` — Viewed 12 frames sampled across 9.1 seconds. Audio could not be assessed.
  - Catalogue items were reused from the earlier identification of this video.
- **Appropriateness reasons:**
  - The stern, camera-facing poses and dramatic framing could feel confrontational to a customer explicitly wary of intimidating imagery, although no overt threat is visible.
  - The simple Yale lettering suits their respect for the university's reputation, but the sequence does not connect it to a young person's academic achievement or community pride.
  - No visible text talks down to rural or working families or contains crude humour; however, the stylised presentation is less aligned with their preference for down-to-earth communication.
- **Fit with this customer:**
  - *Helps:* Prefers plain, sturdy sweatshirts and simple lettering. — The foreground navy hoodie has a simple, prominent white YALE design, though construction quality is not demonstrated.
  - *Hurts:* Would buy only as a gift marking a relative's or family friend's admission or graduation. — The group presentation provides no gift occasion or explanation of whom the garment would suit.
  - *Hurts:* Highly price-sensitive and wants fair pricing, a trustworthy seller, and simple rural delivery. — No price, Campus Customs store name, ordering route, or delivery information appears in the sampled frames.
  - *Hurts:* Often watches on a phone with sound off and gives unfamiliar ads only a few seconds to explain themselves. — Yale apparel is visible immediately, but there is no readable sales message explaining the offer throughout the sampled sequence.
  - *Hurts:* Dislikes unexplained stylised imagery and advertising aimed at campus or city insiders. — The overpass setting, changing camera angles, and posed group make the sequence a stylised presentation rather than a straightforward product demonstration.
- **Recommendations:** Open with a clear hoodie shot and a caption such as 'Celebrate their Yale admission' to establish the gift purpose immediately. End with Campus Customs' name, the actual price, an easy ordering address, and clear delivery timing and rural shipping information. Replace some dramatic close-ups with a friendly gift-giving scene and close views of fabric, seams, and cuffs, supported by verified material and care details.
- **Limitations:** The audio track could not be heard, so spoken messaging and any audio-related suitability concerns cannot be assessed. Only sampled frames were available; brief intervening text or actions may not be represented. Garment durability, actual pricing, and delivery service cannot be established from these frames.

**User commentary** (submitted 2026-10-04T06:42:11Z)

*What did the agent do well?*

> great profile building.  Notes that this farmer has no tie to Yale and has no good reason for purchase.  notes price sensitivity.

*What was bad, or weaker than you would want?*

> This is a bonus profile not required for the project.

*Were there any mistakes? Describe them.*

> This is a bonus profile not required for the project.

*If there were mistakes, how would you try to fix them?*

> This is a bonus profile not required for the project.

#### Family from Beijing touring Yale with their high-school-aged child (`profiles/profile_beijing_family.json`)

- **Scores:** appropriateness 6 / 10 · effectiveness 3 / 10 (ineffective, high confidence)
- **What the agent saw:** The ad shows a foreground figure wearing a navy hoodie with large white YALE lettering, with a group in dark Yale apparel behind them beneath a concrete overpass. The sequence shifts between close-ups, elevated views, and wider group shots, ending in the same setting without visible shopping information.
- **Steps it took:**
  1. `read_customer_profile` — Read profile 'beijing_family': Family from Beijing touring Yale with their high-school-aged child.
  2. `watch_ad_video` — Viewed 12 frames sampled across 9.1 seconds. Audio could not be assessed.
  - Catalogue items were reused from the earlier identification of this video.
- **Appropriateness reasons:**
  - The family's preference for respectful, prestigious university imagery is only partly met: classic Yale lettering is prominent, but the stark overpass setting and intense direct-to-camera presentation could feel off-key.
  - Their concern about university safety makes the isolated-looking setting less reassuring than welcoming campus scenes, although the frames show no threatening act or evidence that Yale is unsafe.
  - Nothing visible belittles study or achievement, but the ad does not reflect the academic heritage and international welcome this family values.
- **Fit with this customer:**
  - *Helps:* Prefers classic navy apparel with clearly shown YALE lettering for keepsakes and gifts. — The foreground navy hoodie repeatedly displays large white YALE lettering.
  - *Hurts:* Values Yale's historic campus, academic reputation, and scenes of student life. — The entire visible sequence takes place under an overpass, with no recognizable campus landmark, library, or classroom.
  - *Hurts:* Responds to prestigious, welcoming, respectful imagery rather than cultural references needing explanation. — The intense poses and stylized group presentation offer little family-visit or academic context.
  - *Hurts:* Relies on visuals and readable on-screen information more than spoken English. — The garment branding is clear, but no explanatory shopping text or Chinese-language information appears.
  - *Hurts:* Needs the shop's location and hours, official-product assurance, and prices; has medium price sensitivity. — No visible store identification, directions, hours, licensing information, or prices support a purchase during the visit.
  - *Hurts:* Buys genuine, good-quality apparel, often several pieces as gifts. — The ad shows apparel being worn but provides no readable quality details or gift-shopping guidance.
- **Recommendations:** Keep the prominent navy YALE hoodie, but show it during a welcoming family campus visit near recognizable historic buildings, with giftable T-shirts alongside it. End with a readable English–Chinese card giving Campus Customs' location, opening hours, shopping link or QR code, and accepted payment methods. Add steady product close-ups with actual prices, fabric details, and verified official-licensing information so the family can assess authenticity, quality, and multiple-gift purchases.
- **Limitations:** Audio was unavailable; speech, music, and other sound could not be assessed. Evenly sampled frames do not establish exact editing pace or exclude brief text between samples. Fabric quality, licensing status, and payment options cannot be verified from the visible apparel.

**User commentary** (submitted 2026-10-04T06:42:43Z)

*What did the agent do well?*

> This is a bonus profile not required for the project.

*What was bad, or weaker than you would want?*

> This is a bonus profile not required for the project.

*Were there any mistakes? Describe them.*

> This is a bonus profile not required for the project.

*If there were mistakes, how would you try to fix them?*

> This is a bonus profile not required for the project.

#### 20-year-old who grew up in a big-city neighbourhood (`profiles/profile_urban_20.json`)

- **Scores:** appropriateness 6 / 10 · effectiveness 6 / 10 (mixed, medium confidence)
- **What the agent saw:** The ad shows a foreground figure wearing a navy hoodie with large white YALE lettering beneath a concrete overpass, with a group in casual collegiate clothing behind them. The sequence alternates close-ups, high-angle views, and wider group shots, ending on the apparel and group rather than shopping information.
- **Steps it took:**
  1. `read_customer_profile` — Read profile 'urban_20': 20-year-old who grew up in a big-city neighbourhood.
  2. `watch_ad_video` — Viewed 12 frames sampled across 9.1 seconds. Audio could not be assessed.
  - Catalogue items were reused from the earlier identification of this video.
- **Appropriateness reasons:**
  - The bold collegiate lettering and casual styling fit this customer's interest in Yale prestige as fashion, without visible campus-exclusivity messaging.
  - The overpass setting, foreground performance poses, and largely stationary background group risk feeling like borrowed hip-hop imagery, directly touching this customer's concern about urban culture used as a costume.
  - No visible mocking or caricature is evident, but the frames do not establish the cultural collaboration or authentic community connection this customer values.
- **Fit with this customer:**
  - *Helps:* Prefers navy hoodies, bold collegiate lettering, and pieces that work with everyday streetwear. — The navy YALE hoodie is repeatedly shown with jeans and alongside sneaker-based outfits.
  - *Helps:* Watches short social videos and skips conventional advertising. — The nine-second sequence uses changing camera angles and close-ups rather than a conventional product sales card.
  - *Hurts:* Values authenticity and dislikes awkward imitation of music-video style. — The overpass staging and foreground-versus-background group composition suggest a music-video visual approach, but offer no visible context establishing credibility.
  - *Hurts:* Needs fit and garment weight to judge a hoodie. — On-body views give some styling information, but tight framing and poses leave overall fit unclear; fabric weight is not demonstrated.
  - *Hurts:* Needs a direct product link, sizing, and shipping information. — None of the sampled frames supplies a shopping destination or those purchase details.
  - *Hurts:* Compares price with familiar streetwear and sportswear brands. — No price or concrete quality information helps justify choosing this hoodie over alternatives.
- **Recommendations:** Add a brief Campus Customs end card and a direct product link or shoppable tag, with actual price and access to sizing and shipping details. Include a clear full-length front and side view of the hoodie, plus a fabric close-up and verified weight or fit information. Make the cultural connection substantive through a genuine creator or community collaboration; give collaborators visible agency and credit rather than relying on an overpass and background group to convey credibility.
- **Limitations:** Audio is unavailable, so the sound-led appeal important to this customer cannot be assessed. Sampled frames cannot establish exact editing rhythm or rule out information between samples; any accompanying caption or shopping link is not provided. The frames do not establish production context, cultural collaboration, fabric weight, or actual sizing.

**User commentary** (submitted 2026-10-04T06:43:20Z)

*What did the agent do well?*

> This is a bonus profile not required for the project.

*What was bad, or weaker than you would want?*

> This is a bonus profile not required for the project.

*Were there any mistakes? Describe them.*

> This is a bonus profile not required for the project.

*If there were mistakes, how would you try to fix them?*

> This is a bonus profile not required for the project.
