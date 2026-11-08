"""Scripts for the second wave of scenarios, same row format as lines_en."""

# Weekend Projects, second half: follows lines_en2.LONG to make a seven-minute episode.
SEVEN = """
A +1.2: Welcome back. If you are just joining us, we are talking to two neighbours who built an observatory out of an old shed.
B: And a printer motor.
C: And a lot of patience.
A: Before the break you mentioned the notebook full of mistakes. Can you tell us about the worst one?
C: The worst one was the floor. We poured concrete on a rainy day, and it never set properly.
B: For a whole month the telescope moved a little every time someone walked past.
A: That must have made the pictures blurry.
B: Every single picture. We thought the camera was broken, so we bought a new one.
C +0.2: Which did not help at all.
A +0.2: Of course not.
C: In the end we cut out the middle of the floor and put a separate concrete post under the telescope.
B: Now you can jump up and down next to it and the stars do not move.
A: So the telescope stands on its own little island.
C: Exactly. The shed can shake as much as it likes.
A: Let us talk about the camera. What do you use today?
B: A simple astronomy camera that plugs into a laptop. It cost about the same as a good pair of shoes.
C: The laptop is older than my daughter. It only runs one program, and that is all it needs to do.
A: And what is the best picture you have taken so far?
B: The Orion nebula, last January. We stacked two hundred short pictures into one.
C: It took four hours to take the pictures and two evenings to put them together.
A +0.2: Two evenings?
B +0.2: Two evenings and a lot of tea.
A: Is that picture hanging somewhere?
C: It is printed on a big canvas in the local library. The librarian asked us for it.
B: Under it there is a small sign that says the picture was taken from a back garden two streets away.
A: People must be surprised by that.
C: They are. A few of them have knocked on our door to ask how to start.
A +0.6: What do you tell them?
B: We tell them to come on a Friday, look through the telescope, and then decide.
C: Most people are happy with binoculars and a star map. Not everyone wants to build a shed.
A: That is honest advice.
B: It is cheaper advice too.
A +0.7: Let us look ahead. What is the next project?
C: A second roof. We want to build a small dome for a smaller telescope, so two groups can watch at once.
B: And a ramp, so people in wheelchairs can reach the eyepiece.
A: That is a lovely idea.
B: One of our regular visitors uses a wheelchair, and right now we have to carry the telescope outside for her.
C: She found the comet last spring before any of us did, so she has earned a proper ramp.
A +0.2: She found a comet?
C +0.2: Not a new one, sadly. But she saw it first.
A: Have you ever thought about turning this into a business?
B: People have asked. But it would stop being fun the moment someone had to pay for it.
C: We prefer to keep it as a club. Anyone can come, and nobody owes anything.
A +0.6: We are almost out of time. One last question for both of you. What does the night sky mean to you now?
B: It used to be something I ignored on the way home. Now it is the first thing I check when I step outside.
C: For me it is the neighbours. I have met more people in this street through the telescope than in ten years of living here.
A: That is a wonderful place to stop. Thank you both again, and good luck with the dome.
B: Thank you.
C +0.2: Thanks for having us.
"""

# One sentence said twice, about twenty seconds apart, inside one 75 s piece.
REFRAIN_CLOSE = """
A: Good morning. Before we go home today, a few things about the trip tomorrow.
B: Is everyone coming?
A: Twenty two people so far, and two more might join us.
B +0.6: That is a full bus.
A: Okay everyone, listen up. The bus leaves at seven sharp, so please do not be late.
B: Do we need to bring our own lunch?
A: Yes, bring lunch and water. There is no shop at the lake.
B: What about the weather? It looked cloudy this morning.
A: The forecast says sun after ten, but pack a rain jacket just in case.
B: And where do we meet?
A: In front of the main gate, next to the red sign.
B: Got it. Main gate, red sign.
A +0.8: One more time, because it matters. The bus leaves at seven sharp, so please do not be late.
B: We will be there.
B +0.6: Can I bring my dog?
A: Sorry, no dogs on the bus this time.
B: Fair enough. And what time do we come back?
A: Around six in the evening, if the traffic is good.
B: Great, thank you.
A: Good. See you all tomorrow morning.
"""

# A meeting, and under it a radio left on in the next room that nobody is listening to.
MEETING = """
A: Thanks for staying late. I only need ten minutes to go through the plan for the open day.
B: No problem. Do we have the final list of stands?
A: We do. Twelve stands inside the hall and four outside in the car park.
C: Four outside? What if it rains?
A: The council lends us two big tents. We put the food stands under them.
B: And the music? Last year the speakers were far too loud for the stands next to them.
A: This year the band plays at the far end of the field, away from everyone else.
C: Good. Who is handling the tickets?
B: I can do the tickets in the morning, but I have to leave at two.
A: Then Peter takes over at two. I will tell him tonight.
C: What about parking? The street was full by ten last time.
A: The school next door lets us use their yard. That gives us another forty places.
B: Perfect. I think that covers everything.
A: One last thing. Please be here by eight to help set up the tables.
C +0.2: Eight o'clock. Fine.
B +0.2: See you then.
"""

RADIO = """
D: This is the evening news on local radio. Traffic on the ring road is moving slowly after an accident near the bridge.
D: The weather will stay dry tonight, with clear skies and light winds from the west.
D: In sport, the town football team won their match on Saturday by two goals to one.
D: The museum on the main square will open late on Thursday for a special exhibition of old maps.
D: Road works on the high street will continue until the end of the month.
D: Tomorrow will be warm and sunny, with temperatures reaching twenty four degrees in the afternoon.
D: The library is looking for volunteers to read stories to children on Saturday mornings.
D: That is all from the news desk. Stay with us for music until midnight.
"""

# An English host and an Arabic-speaking guest, each in their own language.
MIXED = """
A: Good evening, and welcome to the programme. Tonight my guest speaks in Arabic, and I will answer in English.
B: مساء الخير، وشكرا على الدعوة.
A: Let us begin with your work. You restore old houses in the historic part of the city.
B: نعم، أعمل في ترميم البيوت القديمة منذ خمس عشرة سنة.
A: What is the hardest part of the job?
B: أصعب شيء هو العثور على الحجر نفسه الذي بني به البيت أول مرة.
A: Why does it have to be the same stone?
B: لأن الحجر الجديد لا يتنفس مثل القديم، فتظهر الرطوبة في الجدران بعد سنة أو سنتين.
A +0.3: That is fascinating.
B: والخشب كذلك. نستعمل خشبا قديما من بيوت هدمت في مكان آخر.
A: How long does it take to restore one house?
B: البيت الصغير يأخذ سنة تقريبا، والبيت الكبير قد يأخذ ثلاث سنوات.
A: And who lives in these houses after you finish?
B: بعضها يعود لأصحابه، وبعضها يصبح متاحف أو مقاهي صغيرة.
A +0.6: If a young person wants to learn this craft, where should they start?
B: أنصحه أن يبدأ مع معلم قديم، وأن يعمل بيديه قبل أن يقرأ الكتب.
A: Thank you very much for joining us tonight.
B +0.2: شكرا لكم، وإلى اللقاء.
"""
