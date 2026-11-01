# AI Prompt Log

This file records the prompts Brian gave the AI coding assistant (Claude Code) to complete
Homework 3, in order and as typed. Each problem has its own section. Where a problem needed
more than one prompt, a short context line says what the follow-up was responding to.

## Problem 1: Setup and scenario

### Prompt 1

> start a new coding session in MGT 409 called HW #3

### Prompt 2

> We will be working in that Homework 3 folder today.  Here is the scenario.  Campus Customs sells Yale Merch.  We will build an agent that can help with 2 questions.  1.  identify if someone in a photo is wearing a campus customs product so that we might outreach to them.  2. to see if a Campus Customs ad video lands with a given customer profile - i.e. Yale student or parent.   We will use the portkey_api_key for any model calls in the agent.  use the gpt-5.6-luna model for the agents.  In the data folder I have already unzipped some files that we will be working with.

### Prompt 3

Context: the assistant had started exploring the data and planning an agent before being given the problem instructions.

> stop.  don't write an agent.  I'm going to give you instructions.

### Prompt 4

Context: the assistant reported that the course rules file names `gpt-6-astra` while Prompt 2 named `gpt-5.6-luna`.

> Yes.  We WILL use gpt-6-astra for the agents.

## Problem 2: Product catalogue

### Prompt 1

> ok.  Problem 1 is complete.  Problem 2:  throughout this entire homework set, you are going to record a output/harness.md file.  You will keep important notes here throughout the entire project.  Our agent will run inside a secure sandbox.  avoid agent loops that use a token value of over $0.50.   Create a file build_catalogue.py that turns every photo in the data/products folder into a structured catalogue.  In this file, I want you to save a description of the item as well as other fields that will be useful for later matching.  The entire catalogue will be saved to output/catalogue.json.  Put the catalogue entry type in models.py as a pydantic/ pydanticai model.   In order to speed up your search, so you are note searching every image, create a database that sorts these products based on a variety of characteristics.  Here are a few to start: sleeve length, color, tee-shirt v sweatshirt v jacket, make a category for if it is for a certain sport, or college, or school at Yale.  Is it for a particular person - like family member?  If there are other characteristics that you identify that are helpful you can include that too.    Document in harness.md how we have sped up our catalogue build.  document which fields are in the catalogue model "models.py" and why these were chosen.  We will continue to add to this harness file throughout the homework.

### Prompt 2

Context: the assistant asked how to run the full build after measuring about $2.80 to describe all 102 photos with `gpt-6-astra`.

> use luna for the catalogue build

### Prompt 3

> ok.  show me the database for my review

### Prompt 4

> looks pretty good.  Were there any specific concerns you had about the catalogue that you want help clarifying?

### Prompt 5

Context: answering the first of the assistant's five questions about the catalogue.

> 1.  Every item in this dataset is sold at campus customs.  so it will count as a campus custom product, even if it is branded with, e.g. champion as well.

### Prompt 6

Context: answering the remaining questions (colour variants, near-identical products, brand, and the sweatshirt category).

> 2.  If there is a color variant in a photo you are trying to identify, state "possible match" and state the reasons why.  3.  if any agent cannot discriminate between 2 catalogue products, then look at the layout of the similar images themselves in the reference data.  If agent STILL can't tell, then  present both products and say "possible match" asking the user to choose which.    4.  if there is an actual brand  like "brooks brothers, under armor, or port and company, then that is the brand of the garment.  if it is no particular brand, then we will call it "house brand."  5.  You can keep the QZ's, pullovers, and full zip hoodies as sweatshirts.

## Problem 3: Product identification agent

### Prompt 1

> problem 3.  we are building a campus customs agent as 4 files.  1) promts/prompt.md - a system prompt that will load it into the agent.  I will be adding to this file later.  2) agent.py - pydantic agent entry point.  3) tools.py - where you will place the agents tools and other helper functions.  4) models.py - pydantic / pydanticAI structured types.  The first ability will be to take an image and decide whether a Campus Customs product appear in this image.  If it does have a CC product in the images, then identify which one it is.  Implement that tool logic in tools.py and wire it from ageny.py.   use first the fields we created in the database to narrow down the item and can then search images directly when narrowed to a few.  I do not want you searching every individual catalogue imaged.  Pull up the item, with image, from the catalogue in a side bar so it can be made available for immediate purchase.  You may build a shopping cart, but because this agent is only a homework project, I do not want to give it the ability to complete a shopping cart purchase.  Only populate the shopping cart.  Add the structured return type for this ability to models.py as a Pydantic/ PydanticAI model.  (Continue to grow models.py whenever the agent needs a new typed object - that is what this file is for.)  Agent must take an image from the image path in the terminal:  python agent.py --image "data/test_images/example.jpg"  The intent for this is to have campus customs agent to enter under agent.py.  and  -- image is the photo to check for a Campus Customs product.  When we test this, replace the path with a real file under "data/"  Save the agents structured output to "output/identify_product.json" (matching the identify model in models.py) One test image is sufficient.  We will add all four in the next problem.  IN the "output/harness.md" write: 1) how the agents does product identification and delineate the things that we did to make it efficient.  2)  Which fields are in the identify model in models.py and why we chose those fields.

### Prompt 2

> ok.  open that html with the test image

### Prompt 3

> that looks pretty good.

### Prompt 4

> in the harness - make note to the professor that I added the shopping cart feature which was not part of the problem set, but seemed like a natural extension of this project.

### Prompt 5

Context: the assistant asked whether the note should cover the sidebar as well as the cart.

> yes.   sidebar too.  thats good.

## Problem 4: Test the agent on all four photos

### Prompt 1

> problem 4 - Run the agent on all 4 photos in "data/test_images/ ".  After the agent runs and makes its decision on whether it is in the campus customs catalogue or not, please check it vs the file name that containes the word "true" or "false."  this should not be known by the agent, but only a check to the agent's skill.  Produce those results of agent test vs actual (as denoted in the file name).  Save agent't output for all four images to "output/identify_product.json".  Each entry should match the identify Pydantic/PydanticAI model we put in models.py.   Then once its complete, show me the results and ask me to comment on the agent's performance - what it did well, what was bad, and if there were any mistakes.  If there were mistakes, ask me how I would try to fix them.  Save this commentary to "output/agent_evaluation.md"

### Prompt 2

Context: the assistant had presented the results as a table in chat and asked the four review questions there.

> youre going to have to show me these images as well as the agent's thoughts for each one in order for me to comment.  Turn this whole thing into a dynamic HTML form and I will leave my comments right there for you to record.  When I click "submit" that comment will populate the fields in the output/agent_evaluation.md.  clicking submit should then bring up the next photo with agent's thoughts and space for my comments.  Keep that sidebar and shopping cart present for each catalogue item during this evaluation.  If it doesn't exist state in the sidebar "Item is not carried by Campus Customs"

### Prompt 3

> ok.  review my recorded comments.

### Prompt 4

Context: the assistant had explained that the $0.03-per-match cost target would require a cheaper model.

> This portion of the project is done.  There is no need to change the agent's model at this time.  We will move on to Problem 5.

## Problem 5: Ad effectiveness for a customer profile

### Prompt 1

> ok.  Now the agent needs a new ability.  Take a video and a customer profile JSON file and judge how effective the video would be at convincing that customer to shop at Campus Customs (I'm just going to call it CC from now on.)  Put the new tool code in tools.py (the same tools file as identify.)  Update the same prompts/prompt.md so that the agent knows how to use this new ability.  Keep only 1 prompt file - add to it.  do not start a second one.   put the structured result type for this ability in models.py as a Pydantic / PydanticAI model ( the same models.py file as the catalogue and identify types.  Use this terminal command [python agent.py --video "data/videos/ad_humble.mp4" --profile "profiles/profile_student.json"]  In this command --video is the CC ad file.  and --profile is the customer profile JSON to judge against.  You will use the real filenames from the datapack and "profiles/"  Save this agents output for this to run to [output/ad_effectiveness.json] which will match the ad-effectiveness model in models.py.  One profile is sufficient at this time.   In the [output/harness.md] write the tools that you gave the agent for the video and profile job (what each tool does in one short line.)  Also write to the harness.md file which fields are in the ad-effectiveness model in models.py and why we chose them.

### Prompt 2

Context: the assistant flagged that it had written a stand-in student profile and that the agent could not hear the ad's audio.

> i see the 2 issues you brought to my attention.  we will create those profiles in problem 5.  are there any other options for transcription available for this commercial?  are there any other things you need me to clarify?

### Prompt 3

Context: answering the assistant's questions about transcription, profiles, telling the agent what the ad is, and identifying catalogue products in the ad.

> We will leave out transcription at this time and use other parameters to decide.  I can always add it later.  I will define the profiles in Problem 5.  You can pass a 1-line description of the file name to the agent.  If the agent is able to identify a CC catalogue item, yes, it should identify it like earlier.  Make note for the professor and TAs in the harness file that I have specifically asked for the agent to do this, as it is not part of the original assignment.  I do not want them to think there was accidental bleed-over from part A to Part B.

## Problem 6: Customer profiles and the appropriateness meter

### Prompt 1

> So now, problem 6:  Create [profiles/profile_student.json] and [profiles/profile_parent.json]  These will describe a typical Yale student and a  parent of a Yale student.  I want you to include useful fields in these profiles that would matter for whether an ad resonates.  define the profile shape in models.py as a Pydantic / PydanticAI model, then save the filled-in student and parent instances as those JSON files.  In [output/harness.md] explain why you chose those profile fields.  When considering the profile of a Yale student, don't only consider the age.  Consider what the university is known for traditionally and also its modern-day values.   I think we should be able to have the agent give the ad a score of 0-10 for appropriateness.  Make it like an analog sound-mixer needle-style meter with correlating colors red--orange--yellow--green with green being the "10".

## Problem 7: Run the ad for all profiles

### Prompt 1

> ok cool.  Make 3 other profiles.  first, is a middle-aged farmer from Kansas.  second is an family touring from Beijing, checking out the school for their young high school-aged student.  third is a 20 year old who grew up in the urban regions of LA, Chicago, NYC or Miami.  Make note in the harness files that I specifically requested 3 other profiles be built.  Then start Problem 7:  Run the agent on the CC ad video for ALL profiles.  Terminal [python agent.py --video "data/videos/ad_humble.mp4" --profile "profiles/profile_student.json"
> python agent.py --video "data/videos/ad_humble.mp4" --profile "profiles/profile_parent.json"]   This command will run the same video for two different customers.  Replace the paths with our actual video and profile files if appropriate.  Save the structured results for both runs to [output/ad_effectiveness.json] - your ad-effectiveness Pydantic/ PydanticAI model from the models.py.   Present these videos, then  the screenshots provided all embedded into an HTML page for my review.  give me comment boxes like we did earlier for the photo portion of the exercises.  Record what I type into these comment fields in the [output/agent_evaluation.md] file where you will create a new section for these ad runs.  Like last time, present me the first one, then with the click of a button save the result and present the next.

### Prompt 2

> ok  check my reviews

## Problem 8: Safety rules and audit trail

### Prompt 1

> Lets add safety rules for processing images - what agent must or must not do with customer and influencer photos.  Record these rules to the same prompts/prompt.md file.  Make a clearly marked safety section that the agent will load as its system prompt.  Make the agent append to [output/audit_trail.json] on every run:  for each agent loop iteration, record enough to audit later - time, thoughts, tool names + args + short result, stop reasons.  Append this as the agent runs - do not wipe the file each time.    Put an audit-entry type in models.py as a Pydantic/ PydanticAI model so each appended record is structured in the same way.  In [output/harness.md]  state which audit fields you included and why.  Run the agent on 1 test image and also the video file, so that the audit file as real data in it.  Then open that file in an HTML form demonstrating the rules that we created and show me the data in that file.

## Problem 9: Complete the harness document

### Prompt 1

> Problem 9: Complete [output/harness.md] so a manager could understand this system.  Include: 1) all tools the agent uses.  2) its abilities (identify product in image, judge ad for a profile, shopping cart feature and all other features.) 3) the Pydantic / PydanticAI models in models.py - what each type is for and why its fields were chosen.  4) the safety rules.  5) Specs such as max loop interations, frame sampling rate from videos and other limits that matter for cost or quality.   Keep all earlier harness instructions (catalogue speedup, field choices, identify efficiency, profile fields, video tools.)  This entire project should be made coherent and complete.  Produce an executive level summary with top page features and then a more detailed report to follow based on interest in HTML format.  Put some cool "BMo" (My initials) brass stamp monogram logo on this web page.

## Problem 10: Submit zip

### Prompt 1

Context: sent with a screenshot of the Problem 10 instructions (folder named `hw3`, zipped as `hw3.zip`, no real `.env`, `.env.example` with placeholders, and the expected file layout).

> This is problem 10 - packaging it all into a zip.  Please also be sure to include all HTML files that we created and make them executable by the AI review tool, the TAs, and the professor.

## Review comments entered in the review form

Brian's comments on the agent's performance were typed into the review form rather than
into the chat. They are recorded in `output/agent_evaluation.md`.
