"""Word lists for whimsical name generation.

Adapted from Docker's names-generator.go
(https://github.com/docker-archive/docker-ce/blob/master/components/engine/pkg/namesgenerator/names-generator.go),
licensed under the Apache License 2.0. See LICENSE-NOTICE.md.
Supplementary surnames appended from docs/new-names.txt.
"""

ADJECTIVES: tuple[str, ...] = (
    "admiring",
    "adoring",
    "affectionate",
    "agitated",
    "amazing",
    "analytical",
    "angry",
    "awesome",
    "beautiful",
    "blissful",
    "bold",
    "boring",
    "brave",
    "busy",
    "charming",
    "clever",
    "cool",
    "compassionate",
    "competent",
    "condescending",
    "confident",
    "cranky",
    "crazy",
    "curious",
    "dazzling",
    "determined",
    "diligent",
    "distracted",
    "dreamy",
    "eager",
    "ecstatic",
    "elastic",
    "elated",
    "elegant",
    "eloquent",
    "empathetic",
    "energetic",
    "enthusiastic",
    "epic",
    "exciting",
    "fervent",
    "festive",
    "flamboyant",
    "focused",
    "friendly",
    "frosty",
    "funny",
    "gallant",
    "gifted",
    "goofy",
    "gracious",
    "great",
    "happy",
    "hardcore",
    "heuristic",
    "hopeful",
    "hungry",
    "imaginative",
    "ingenious",
    "infallible",
    "inspiring",
    "interesting",
    "intelligent",
    "inventive",
    "jolly",
    "jovial",
    "keen",
    "kind",
    "laughing",
    "loving",
    "lucid",
    "magical",
    "methodical",
    "meticulous",
    "modest",
    "musing",
    "mystifying",
    "naughty",
    "nervous",
    "nice",
    "nifty",
    "nostalgic",
    "objective",
    "optimistic",
    "patient",
    "peaceful",
    "pedantic",
    "pensive",
    "practical",
    "pragmatic",
    "priceless",
    "quirky",
    "quizzical",
    "recursing",
    "relaxed",
    "resilient",
    "resourceful",
    "reverent",
    "romantic",
    "sad",
    "secure",
    "serene",
    "sharp",
    "silly",
    "sleepy",
    "steadfast",
    "stoic",
    "strange",
    "stupefied",
    "suspicious",
    "sweet",
    "tender",
    "tenacious",
    "thirsty",
    "thoughtful",
    "trusting",
    "unruffled",
    "upbeat",
    "vibrant",
    "vigilant",
    "vigorous",
    "visionary",
    "witty",
    "wizardly",
    "wonderful",
    "xenodochial",
    "youthful",
    "zealous",
    "zen",
)

SURNAMES: tuple[str, ...] = (
    # Maria Gaetana Agnesi - Italian mathematician, philosopher, theologian and humanitarian. She was the first woman to write a mathematics handbook and the first woman appointed as a Mathematics Professor at a university. https://en.wikipedia.org/wiki/Maria_Gaetana_Agnesi
    "agnesi",
    # Muhammad ibn Jābir al-Ḥarrānī al-Battānī was a founding father of astronomy. https://en.wikipedia.org/wiki/Mu%E1%B8%A5ammad_ibn_J%C4%81bir_al-%E1%B8%A4arr%C4%81n%C4%AB_al-Batt%C4%81n%C4%A1
    "albattani",
    # Frances E. Allen, became the first female IBM Fellow in 1989. In 2006, she became the first female recipient of the ACM's Turing Award. https://en.wikipedia.org/wiki/Frances_E._Allen
    "allen",
    # June Almeida - Scottish virologist who took the first pictures of the rubella virus - https://en.wikipedia.org/wiki/June_Almeida
    "almeida",
    # Kathleen Antonelli, American computer programmer and one of the six original programmers of the ENIAC - https://en.wikipedia.org/wiki/Kathleen_Antonelli
    "antonelli",
    # Archimedes was a physicist, engineer and mathematician who invented too many things to list them here. https://en.wikipedia.org/wiki/Archimedes
    "archimedes",
    # Maria Ardinghelli - Italian translator, mathematician and physicist - https://en.wikipedia.org/wiki/Maria_Ardinghelli
    "ardinghelli",
    # Aryabhata - Ancient Indian mathematician-astronomer during 476-550 CE https://en.wikipedia.org/wiki/Aryabhata
    "aryabhata",
    # Wanda Austin - Wanda Austin is the President and CEO of The Aerospace Corporation, a leading architect for the US security space programs. https://en.wikipedia.org/wiki/Wanda_Austin
    "austin",
    # Charles Babbage invented the concept of a programmable computer. https://en.wikipedia.org/wiki/Charles_Babbage.
    "babbage",
    # Stefan Banach - Polish mathematician, was one of the founders of modern functional analysis. https://en.wikipedia.org/wiki/Stefan_Banach
    "banach",
    # Buckaroo Banzai and his mentor Dr. Hikita perfected the "oscillation overthruster", a device that allows one to pass through solid matter. - https://en.wikipedia.org/wiki/The_Adventures_of_Buckaroo_Banzai_Across_the_8th_Dimension
    "banzai",
    # John Bardeen co-invented the transistor - https://en.wikipedia.org/wiki/John_Bardeen
    "bardeen",
    # Jean Bartik, born Betty Jean Jennings, was one of the original programmers for the ENIAC computer. https://en.wikipedia.org/wiki/Jean_Bartik
    "bartik",
    # Laura Bassi, the world's first female professor https://en.wikipedia.org/wiki/Laura_Bassi
    "bassi",
    # Hugh Beaver, British engineer, founder of the Guinness Book of World Records https://en.wikipedia.org/wiki/Hugh_Beaver
    "beaver",
    # Alexander Graham Bell - an eminent Scottish-born scientist, inventor, engineer and innovator who is credited with inventing the first practical telephone - https://en.wikipedia.org/wiki/Alexander_Graham_Bell
    "bell",
    # Karl Friedrich Benz - a German automobile engineer. Inventor of the first practical motorcar. https://en.wikipedia.org/wiki/Karl_Benz
    "benz",
    # Homi J Bhabha - was an Indian nuclear physicist, founding director, and professor of physics at the Tata Institute of Fundamental Research. https://en.wikipedia.org/wiki/Homi_J._Bhabha
    "bhabha",
    # Bhaskara II - Ancient Indian mathematician-astronomer whose work on calculus predates Newton and Leibniz by over half a millennium - https://en.wikipedia.org/wiki/Bh%C4%81skara_II
    "bhaskara",
    # Sue Black - British computer scientist and campaigner. She has been instrumental in saving Bletchley Park, the site of World War II codebreaking - https://en.wikipedia.org/wiki/Sue_Black_(computer_scientist)
    "black",
    # Elizabeth Helen Blackburn - Australian-American Nobel laureate; best known for co-discovering telomerase. https://en.wikipedia.org/wiki/Elizabeth_Blackburn
    "blackburn",
    # Elizabeth Blackwell - American doctor and first American woman to receive a medical degree - https://en.wikipedia.org/wiki/Elizabeth_Blackwell
    "blackwell",
    # Niels Bohr is the father of quantum theory. https://en.wikipedia.org/wiki/Niels_Bohr.
    "bohr",
    # Kathleen Booth, she's credited with writing the first assembly language. https://en.wikipedia.org/wiki/Kathleen_Booth
    "booth",
    # Anita Borg - Anita Borg was the founding director of the Institute for Women and Technology (IWT). https://en.wikipedia.org/wiki/Anita_Borg
    "borg",
    # Satyendra Nath Bose - He provided the foundation for Bose–Einstein statistics and the theory of the Bose–Einstein condensate. - https://en.wikipedia.org/wiki/Satyendra_Nath_Bose
    "bose",
    # Katherine Louise Bouman is an imaging scientist and Assistant Professor of Computer Science at the California Institute of Technology. She researches computational methods for imaging. https://en.wikipedia.org/wiki/Katherine_Bouman
    "bouman",
    # Evelyn Boyd Granville - She was one of the first African-American woman to receive a Ph.D. in mathematics; she earned it in 1949 from Yale University. https://en.wikipedia.org/wiki/Evelyn_Boyd_Granville
    "boyd",
    # Brahmagupta - Ancient Indian mathematician during 598-670 CE who gave rules to compute with zero - https://en.wikipedia.org/wiki/Brahmagupta
    "brahmagupta",
    # Walter Houser Brattain co-invented the transistor - https://en.wikipedia.org/wiki/Walter_Houser_Brattain
    "brattain",
    # Emmett Brown invented time travel. https://en.wikipedia.org/wiki/Emmett_Brown (thanks Brian Goff)
    "brown",
    # Linda Brown Buck - American biologist and Nobel laureate best known for her genetic and molecular analyses of the mechanisms of smell. https://en.wikipedia.org/wiki/Linda_B._Buck
    "buck",
    # Dame Susan Jocelyn Bell Burnell - Northern Irish astrophysicist who discovered radio pulsars and was the first to analyse them. https://en.wikipedia.org/wiki/Jocelyn_Bell_Burnell
    "burnell",
    # Annie Jump Cannon - pioneering female astronomer who classified hundreds of thousands of stars and created the system we use to understand stars today. https://en.wikipedia.org/wiki/Annie_Jump_Cannon
    "cannon",
    # Rachel Carson - American marine biologist and conservationist, her book Silent Spring and other writings are credited with advancing the global environmental movement. https://en.wikipedia.org/wiki/Rachel_Carson
    "carson",
    # Dame Mary Lucy Cartwright - British mathematician who was one of the first to study what is now known as chaos theory. https://en.wikipedia.org/wiki/Mary_Lucy_Cartwright
    "cartwright",
    # George Washington Carver - American agricultural scientist and inventor. He was the most prominent black scientist of the early 20th century. https://en.wikipedia.org/wiki/George_Washington_Carver
    "carver",
    # Vinton Gray Cerf - American Internet pioneer, recognised as one of "the fathers of the Internet". https://en.wikipedia.org/wiki/Vint_Cerf
    "cerf",
    # Subrahmanyan Chandrasekhar - Astrophysicist known for his mathematical theory on different stages and evolution in structures of the stars. https://en.wikipedia.org/wiki/Subrahmanyan_Chandrasekhar
    "chandrasekhar",
    # Sergey Alexeyevich Chaplygin (Russian: Серге́й Алексе́евич Чаплы́гин) was a Russian and Soviet physicist, mathematician, and mechanician. https://en.wikipedia.org/wiki/Sergey_Chaplygin
    "chaplygin",
    # Émilie du Châtelet - French natural philosopher, mathematician, physicist, and author; known for translation and commentary on Newton's Principia. https://en.wikipedia.org/wiki/%C3%89milie_du_Ch%C3%A2telet
    "chatelet",
    # Asima Chatterjee was an Indian organic chemist noted for her research on vinca alkaloids and drug development. https://en.wikipedia.org/wiki/Asima_Chatterjee
    "chatterjee",
    # David Lee Chaum - American computer scientist and cryptographer. Known for his contributions to anonymous communication. https://en.wikipedia.org/wiki/David_Chaum
    "chaum",
    # Pafnuty Chebyshev - Russian mathematician. He is known for works on probability, statistics, mechanics, analytical geometry and number theory https://en.wikipedia.org/wiki/Pafnuty_Chebyshev
    "chebyshev",
    # Joan Clarke - Bletchley Park code breaker during the Second World War who pioneered techniques that remained top secret for decades. https://en.wikipedia.org/wiki/Joan_Clarke
    "clarke",
    # Bram Cohen - American computer programmer and author of the BitTorrent peer-to-peer protocol. https://en.wikipedia.org/wiki/Bram_Cohen
    "cohen",
    # Jane Colden - American botanist widely considered the first female American botanist - https://en.wikipedia.org/wiki/Jane_Colden
    "colden",
    # Gerty Theresa Cori - American biochemist who became the third woman—and first American woman—to win a Nobel Prize in science. https://en.wikipedia.org/wiki/Gerty_Cori
    "cori",
    # Seymour Roger Cray was an American electrical engineer and supercomputer architect. https://en.wikipedia.org/wiki/Seymour_Cray
    "cray",
    # Joan Curran was a Welsh scientist who developed radar and invented chaff. https://en.wikipedia.org/wiki/Joan_Curran
    "curran",
    # Marie Curie discovered radioactivity. https://en.wikipedia.org/wiki/Marie_Curie.
    "curie",
    # Charles Darwin established the principles of natural evolution. https://en.wikipedia.org/wiki/Charles_Darwin.
    "darwin",
    # Leonardo Da Vinci invented too many things to list here. https://en.wikipedia.org/wiki/Leonardo_da_Vinci.
    "davinci",
    # A. K. (Alexander Keewatin) Dewdney, Canadian mathematician, computer scientist, author and filmmaker. https://en.wikipedia.org/wiki/Alexander_Dewdney
    "dewdney",
    # Satish Dhawan - Indian mathematician and aerospace engineer, known for leading the successful development of the Indian space programme. https://en.wikipedia.org/wiki/Satish_Dhawan
    "dhawan",
    # Bailey Whitfield Diffie - American cryptographer and one of the pioneers of public-key cryptography. https://en.wikipedia.org/wiki/Whitfield_Diffie
    "diffie",
    # Edsger Wybe Dijkstra was a Dutch computer scientist and mathematical scientist. https://en.wikipedia.org/wiki/Edsger_W._Dijkstra.
    "dijkstra",
    # Paul Adrien Maurice Dirac - English theoretical physicist who made fundamental contributions to both quantum mechanics and quantum electrodynamics. https://en.wikipedia.org/wiki/Paul_Dirac
    "dirac",
    # Agnes Meyer Driscoll - American cryptanalyst during World Wars I and II. https://en.wikipedia.org/wiki/Agnes_Meyer_Driscoll
    "driscoll",
    # Donna Dubinsky - played an integral role in the development of personal digital assistants. https://en.wikipedia.org/wiki/Donna_Dubinsky
    "dubinsky",
    # Annie Easley - She was a leading member of the team which developed software for the Centaur rocket stage. https://en.wikipedia.org/wiki/Annie_Easley
    "easley",
    # Thomas Alva Edison, prolific inventor https://en.wikipedia.org/wiki/Thomas_Edison
    "edison",
    # Albert Einstein invented the general theory of relativity. https://en.wikipedia.org/wiki/Albert_Einstein
    "einstein",
    # Alexandra Asanovna Elbakyan is a Kazakhstani computer programmer and internet activist. https://en.wikipedia.org/wiki/Alexandra_Elbakyan
    "elbakyan",
    # Taher A. ElGamal - Egyptian cryptographer best known for the ElGamal cryptosystem and signature scheme. https://en.wikipedia.org/wiki/Taher_ElGamal
    "elgamal",
    # Gertrude Elion - American biochemist, pharmacologist and Nobel laureate. https://en.wikipedia.org/wiki/Gertrude_Elion
    "elion",
    # James Henry Ellis - British engineer and cryptographer employed by the GCHQ. https://en.wikipedia.org/wiki/James_H._Ellis
    "ellis",
    # Douglas Engelbart gave the mother of all demos: https://en.wikipedia.org/wiki/Douglas_Engelbart
    "engelbart",
    # Euclid invented geometry. https://en.wikipedia.org/wiki/Euclid
    "euclid",
    # Leonhard Euler invented large parts of modern mathematics. https://en.wikipedia.org/wiki/Leonhard_Euler
    "euler",
    # Michael Faraday - British scientist who contributed to electromagnetism and electrochemistry. https://en.wikipedia.org/wiki/Michael_Faraday
    "faraday",
    # Horst Feistel - German-born American cryptographer who co-developed DES and Lucifer. https://en.wikipedia.org/wiki/Horst_Feistel
    "feistel",
    # Pierre de Fermat pioneered several aspects of modern mathematics. https://en.wikipedia.org/wiki/Pierre_de_Fermat
    "fermat",
    # Enrico Fermi invented the first nuclear reactor. https://en.wikipedia.org/wiki/Enrico_Fermi.
    "fermi",
    # Richard Feynman was a key contributor to quantum mechanics and particle physics. https://en.wikipedia.org/wiki/Richard_Feynman
    "feynman",
    # Benjamin Franklin is famous for his experiments in electricity and the invention of the lightning rod.
    "franklin",
    # Yuri Alekseyevich Gagarin - Soviet pilot and cosmonaut, first human in outer space. https://en.wikipedia.org/wiki/Yuri_Gagarin
    "gagarin",
    # Galileo was a founding father of modern astronomy, and faced politics and obscurantism to establish scientific truth.  https://en.wikipedia.org/wiki/Galileo_Galilei
    "galileo",
    # Évariste Galois - French mathematician whose work laid the foundations of Galois theory and group theory. https://en.wikipedia.org/wiki/%C3%89variste_Galois
    "galois",
    # Kadambini Ganguly - Indian physician, known for being the first South Asian female physician trained in western medicine to graduate in South Asia. https://en.wikipedia.org/wiki/Kadambini_Ganguly
    "ganguly",
    # William Henry "Bill" Gates III is an American business magnate and computer programmer. https://en.wikipedia.org/wiki/Bill_Gates
    "gates",
    # Johann Carl Friedrich Gauss - German mathematician who made significant contributions to many fields. https://en.wikipedia.org/wiki/Carl_Friedrich_Gauss
    "gauss",
    # Marie-Sophie Germain - French mathematician, physicist and philosopher. https://en.wikipedia.org/wiki/Sophie_Germain
    "germain",
    # Adele Goldberg, was one of the designers and developers of the Smalltalk language. https://en.wikipedia.org/wiki/Adele_Goldberg_(computer_scientist)
    "goldberg",
    # Adele Goldstine, born Adele Katz, wrote the complete technical description for the first electronic digital computer, ENIAC. https://en.wikipedia.org/wiki/Adele_Goldstine
    "goldstine",
    # Shafi Goldwasser is a computer scientist known for creating theoretical foundations of modern cryptography. https://en.wikipedia.org/wiki/Shafi_Goldwasser
    "goldwasser",
    # James Golick, all around gangster.
    "golick",
    # Jane Goodall - British primatologist and anthropologist. https://en.wikipedia.org/wiki/Jane_Goodall
    "goodall",
    # Stephen Jay Gould was was an American paleontologist and evolutionary biologist. https://en.wikipedia.org/wiki/Stephen_Jay_Gould
    "gould",
    # Sheldon Glashow - American physicist; co-discoverer of the electroweak theory and Nobel laureate. https://en.wikipedia.org/wiki/Sheldon_Glashow
    "glashow",
    # Carolyn Widney Greider - American molecular biologist and Nobel laureate. https://en.wikipedia.org/wiki/Carol_W._Greider
    "greider",
    # Alexander Grothendieck - German-born French mathematician who became a leading figure in modern algebraic geometry. https://en.wikipedia.org/wiki/Alexander_Grothendieck
    "grothendieck",
    # Lois Haibt - American computer scientist, part of the team at IBM that developed FORTRAN. https://en.wikipedia.org/wiki/Lois_Haibt
    "haibt",
    # Margaret Hamilton - Director of the Software Engineering Division of the MIT Instrumentation Laboratory. https://en.wikipedia.org/wiki/Margaret_Hamilton_(software_engineer)
    "hamilton",
    # Caroline Harriet Haslett - English electrical engineer and champion of women's rights. https://en.wikipedia.org/wiki/Caroline_Haslett
    "haslett",
    # Stephen Hawking pioneered the field of cosmology by combining general relativity and quantum mechanics. https://en.wikipedia.org/wiki/Stephen_Hawking
    "hawking",
    # Martin Edward Hellman - American cryptologist, best known for his invention of public-key cryptography. https://en.wikipedia.org/wiki/Martin_Hellman
    "hellman",
    # Werner Heisenberg was a founding father of quantum mechanics. https://en.wikipedia.org/wiki/Werner_Heisenberg
    "heisenberg",
    # Grete Hermann was a German philosopher noted for her work on the foundations of quantum mechanics. https://en.wikipedia.org/wiki/Grete_Hermann
    "hermann",
    # Caroline Lucretia Herschel - German astronomer and discoverer of several comets. https://en.wikipedia.org/wiki/Caroline_Herschel
    "herschel",
    # Heinrich Rudolf Hertz - German physicist who first conclusively proved the existence of electromagnetic waves. https://en.wikipedia.org/wiki/Heinrich_Hertz
    "hertz",
    # Jaroslav Heyrovský was the inventor of the polarographic method. https://en.wikipedia.org/wiki/Jaroslav_Heyrovsk%C3%BD
    "heyrovsky",
    # Dorothy Hodgkin was a British biochemist credited with developing protein crystallography. https://en.wikipedia.org/wiki/Dorothy_Hodgkin
    "hodgkin",
    # Douglas R. Hofstadter is an American professor of cognitive science and author of G%C3%B6del, Escher, Bach. https://en.wikipedia.org/wiki/Douglas_Hofstadter
    "hofstadter",
    # Erna Schneider Hoover revolutionized modern communication by inventing a computerized telephone switching method. https://en.wikipedia.org/wiki/Erna_Schneider_Hoover
    "hoover",
    # Grace Hopper developed the first compiler for a computer programming language. https://en.wikipedia.org/wiki/Grace_Hopper
    "hopper",
    # Frances Hugle, she was an American scientist, engineer, and inventor who contributed to semiconductors and integrated circuitry. https://en.wikipedia.org/wiki/Frances_Hugle
    "hugle",
    # Edwin Hubble - American astronomer whose observations established the expansion of the universe. https://en.wikipedia.org/wiki/Edwin_Hubble
    "hubble",
    # Hypatia - Greek mathematician and philosopher in Alexandria. https://en.wikipedia.org/wiki/Hypatia
    "hypatia",
    # Teruko Ishizaka - Japanese scientist and immunologist who co-discovered the antibody class Immunoglobulin E. https://en.wikipedia.org/wiki/Teruko_Ishizaka
    "ishizaka",
    # Mary Jackson, American mathematician and aerospace engineer. https://en.wikipedia.org/wiki/Mary_Jackson_(engineer)
    "jackson",
    # Yeong-Sil Jang was a Korean scientist and astronomer during the Joseon Dynasty. https://en.wikipedia.org/wiki/Jang_Yeong-sil
    "jang",
    # Mae Carol Jemison - American engineer, physician, and former NASA astronaut. https://en.wikipedia.org/wiki/Mae_Jemison
    "jemison",
    # Betty Jennings - one of the original programmers of the ENIAC. https://en.wikipedia.org/wiki/Betty_Holberton
    "jennings",
    # Mary Lou Jepsen, was the founder and CTO of One Laptop Per Child. https://en.wikipedia.org/wiki/Mary_Lou_Jepsen
    "jepsen",
    # Katherine Coleman Goble Johnson - American physicist and mathematician who contributed to NASA's spaceflight programs. https://en.wikipedia.org/wiki/Katherine_Johnson
    "johnson",
    # Irène Joliot-Curie - French scientist awarded the Nobel Prize in Chemistry. https://en.wikipedia.org/wiki/Ir%C3%A8ne_Joliot-Curie
    "joliot",
    # Karen Spärck Jones came up with the concept of inverse document frequency. https://en.wikipedia.org/wiki/Karen_Sp%C3%A4rck_Jones
    "jones",
    # A. P. J. Abdul Kalam - is an Indian scientist aka Missile Man of India for his work on ballistic missile and launch vehicle technology. https://en.wikipedia.org/wiki/A._P._J._Abdul_Kalam
    "kalam",
    # Sergey Petrovich Kapitsa was a Russian physicist and demographer. https://en.wikipedia.org/wiki/Sergei_Kapitsa
    "kapitsa",
    # Susan Kare created the icons and many interface elements for the original Apple Macintosh. https://en.wikipedia.org/wiki/Susan_Kare
    "kare",
    # Mstislav Keldysh - Soviet scientist in mathematics and mechanics. https://en.wikipedia.org/wiki/Mstislav_Keldysh
    "keldysh",
    # Mary Kenneth Keller became the first American woman to earn a PhD in Computer Science. https://en.wikipedia.org/wiki/Mary_Kenneth_Keller
    "keller",
    # Johannes Kepler, German astronomer known for his three laws of planetary motion. https://en.wikipedia.org/wiki/Johannes_Kepler
    "kepler",
    # Omar Khayyam - Persian mathematician, astronomer and poet; known for classifying cubic equations. https://en.wikipedia.org/wiki/Omar_Khayy%C3%A1m
    "khayyam",
    # Har Gobind Khorana - Indian-American biochemist who shared the 1968 Nobel Prize for Physiology. https://en.wikipedia.org/wiki/Har_Gobind_Khorana
    "khorana",
    # Jack Kilby invented silicon integrated circuits. https://en.wikipedia.org/wiki/Jack_Kilby
    "kilby",
    # Maria Kirch - German astronomer and first woman to discover a comet. https://en.wikipedia.org/wiki/Maria_Margarethe_Kirch
    "kirch",
    # Donald Knuth - American computer scientist and author of The Art of Computer Programming. https://en.wikipedia.org/wiki/Donald_Knuth
    "knuth",
    # Sophie Kowalevski - Russian mathematician responsible for important contributions to analysis and mechanics. https://en.wikipedia.org/wiki/Sofia_Kovalevskaya
    "kowalevski",
    # Marie-Jeanne de Lalande - French astronomer, mathematician and cataloguer of stars. https://en.wikipedia.org/wiki/Marie-Jeanne_de_Lalande
    "lalande",
    # Hedy Lamarr - Actress and inventor whose frequency-hopping ideas underpin modern Wi-Fi and Bluetooth. https://en.wikipedia.org/wiki/Hedy_Lamarr
    "lamarr",
    # Leslie B. Lamport - American computer scientist known for distributed systems and the Turing Award. https://en.wikipedia.org/wiki/Leslie_Lamport
    "lamport",
    # Mary Leakey - British paleoanthropologist who discovered the first fossilized Proconsul skull. https://en.wikipedia.org/wiki/Mary_Leakey
    "leakey",
    # Henrietta Swan Leavitt - American astronomer who discovered the relation between luminosity and Cepheid period. https://en.wikipedia.org/wiki/Henrietta_Swan_Leavitt
    "leavitt",
    # Esther Miriam Zimmer Lederberg - American microbiologist and a pioneer of bacterial genetics. https://en.wikipedia.org/wiki/Esther_Lederberg
    "lederberg",
    # Inge Lehmann - Danish seismologist and geophysicist who discovered the Earth's inner core. https://en.wikipedia.org/wiki/Inge_Lehmann
    "lehmann",
    # Daniel Lewin - Mathematician and Akamai co-founder. https://en.wikipedia.org/wiki/Daniel_Lewin
    "lewin",
    # Ruth Lichterman - one of the original programmers of the ENIAC. https://en.wikipedia.org/wiki/Ruth_Teitelbaum
    "lichterman",
    # Barbara Liskov - computer scientist who co-developed the Liskov substitution principle. https://en.wikipedia.org/wiki/Barbara_Liskov
    "liskov",
    # Ada Lovelace invented the first algorithm. https://en.wikipedia.org/wiki/Ada_Lovelace
    "lovelace",
    # Auguste and Louis Lumière - the first filmmakers in history. https://en.wikipedia.org/wiki/Auguste_and_Louis_Lumi%C3%A8re
    "lumiere",
    # Mahavira - Ancient Indian mathematician who discovered basic algebraic identities. https://en.wikipedia.org/wiki/Mah%C4%81v%C4%ABra_(mathematician)
    "mahavira",
    # Lynn Margulis - American evolutionary theorist and biologist. https://en.wikipedia.org/wiki/Lynn_Margulis
    "margulis",
    # Yukihiro Matsumoto - Japanese computer scientist and software programmer; chief designer of Ruby. https://en.wikipedia.org/wiki/Yukihiro_Matsumoto
    "matsumoto",
    # James Clerk Maxwell - Scottish physicist, best known for electromagnetic theory. https://en.wikipedia.org/wiki/James_Clerk_Maxwell
    "maxwell",
    # Maria Mayer - American theoretical physicist and Nobel laureate. https://en.wikipedia.org/wiki/Maria_Mayer
    "mayer",
    # John McCarthy invented LISP. https://en.wikipedia.org/wiki/John_McCarthy_(computer_scientist)
    "mccarthy",
    # Barbara McClintock - distinguished American cytogeneticist and Nobel laureate. https://en.wikipedia.org/wiki/Barbara_McClintock
    "mcclintock",
    # Anne Laura Dorinthea McLaren - British developmental biologist whose work helped lead to IVF. https://en.wikipedia.org/wiki/Anne_McLaren
    "mclaren",
    # Malcolm McLean invented the modern shipping container. https://en.wikipedia.org/wiki/Malcolm_McLean
    "mclean",
    # Kay McNulty - one of the original programmers of the ENIAC. https://en.wikipedia.org/wiki/Kathleen_Antonelli
    "mcnulty",
    # Gregor Johann Mendel - Czech scientist and founder of genetics. https://en.wikipedia.org/wiki/Gregor_Mendel
    "mendel",
    # Dmitri Mendeleev - chemist who formulated the periodic law. https://en.wikipedia.org/wiki/Dmitri_Mendeleev
    "mendeleev",
    # Lise Meitner - Austrian/Swedish physicist involved in the discovery of nuclear fission. https://en.wikipedia.org/wiki/Lise_Meitner
    "meitner",
    # Carla Meninsky, game designer and programmer for Atari 2600 classics. https://en.wikipedia.org/wiki/Carla_Meninsky
    "meninsky",
    # Ralph C. Merkle - American computer scientist known for Merkle puzzles and Merkle trees. https://en.wikipedia.org/wiki/Ralph_Merkle
    "merkle",
    # Johanna Mestorf - German prehistoric archaeologist and first female museum director in Germany. https://en.wikipedia.org/wiki/Johanna_Mestorf
    "mestorf",
    # Maryam Mirzakhani - Iranian mathematician and the first woman to win the Fields Medal. https://en.wikipedia.org/wiki/Maryam_Mirzakhani
    "mirzakhani",
    # Rita Levi-Montalcini - Nobel laureate in Physiology or Medicine. https://en.wikipedia.org/wiki/Rita_Levi-Montalcini
    "montalcini",
    # Gordon Earle Moore - American engineer and Silicon Valley founder. https://en.wikipedia.org/wiki/Gordon_Moore
    "moore",
    # Samuel Morse - contributed to the invention of the Morse code telegraph system. https://en.wikipedia.org/wiki/Samuel_Morse
    "morse",
    # Ian Murdock - founder of the Debian project. https://en.wikipedia.org/wiki/Ian_Murdock
    "murdock",
    # May-Britt Moser - Nobel laureate neuroscientist who helped discover grid cells. https://en.wikipedia.org/wiki/May-Britt_Moser
    "moser",
    # John Napier of Merchiston - Scottish mathematician known for logarithms. https://en.wikipedia.org/wiki/John_Napier
    "napier",
    # John Forbes Nash, Jr. - American mathematician who made fundamental contributions to game theory. https://en.wikipedia.org/wiki/John_Forbes_Nash
    "nash",
    # John von Neumann - computer architectures are based on the von Neumann architecture. https://en.wikipedia.org/wiki/John_von_Neumann
    "neumann",
    # Isaac Newton invented classic mechanics and modern optics. https://en.wikipedia.org/wiki/Isaac_Newton
    "newton",
    # Florence Nightingale, more prominently known as a nurse, also pioneered statistical graphics. https://en.wikipedia.org/wiki/Florence_Nightingale
    "nightingale",
    # Alfred Nobel - a Swedish chemist, engineer, innovator, and armaments manufacturer. https://en.wikipedia.org/wiki/Alfred_Nobel
    "nobel",
    # Emmy Noether, German mathematician. Noether's theorem is named after her. https://en.wikipedia.org/wiki/Emmy_Noether
    "noether",
    # Poppy Northcutt. Poppy Northcutt was the first woman to work as part of NASA’s Mission Control. https://en.wikipedia.org/wiki/Poppy_Northcutt
    "northcutt",
    # Robert Noyce invented silicon integrated circuits and gave Silicon Valley its name. https://en.wikipedia.org/wiki/Robert_Noyce
    "noyce",
    # Panini - Ancient Indian linguist and grammarian from the 4th century CE. https://en.wikipedia.org/wiki/P%C4%81%E1%B9%87ini
    "panini",
    # Max Planck - German physicist and originator of quantum theory. https://en.wikipedia.org/wiki/Max_Planck
    "planck",
    # Wolfgang Pauli - Austrian physicist; formulated the Pauli exclusion principle. https://en.wikipedia.org/wiki/Wolfgang_Pauli
    "pauli",
    # Ambroise Pare invented modern surgery. https://en.wikipedia.org/wiki/Ambroise_Par%C3%A9
    "pare",
    # Blaise Pascal, French mathematician, physicist, and inventor. https://en.wikipedia.org/wiki/Blaise_Pascal
    "pascal",
    # Louis Pasteur discovered vaccination and pasteurization. https://en.wikipedia.org/wiki/Louis_Pasteur.
    "pasteur",
    # Cecilia Payne-Gaposchkin was an astronomer and astrophysicist who explained stellar composition. https://en.wikipedia.org/wiki/Cecilia_Payne-Gaposchkin
    "payne",
    # Radia Perlman is a software designer and network engineer. https://en.wikipedia.org/wiki/Radia_Perlman
    "perlman",
    # Rob Pike was a key contributor to Unix, Plan 9, and the Go programming language. https://en.wikipedia.org/wiki/Rob_Pike
    "pike",
    # Henri Poincaré made fundamental contributions in several fields of mathematics. https://en.wikipedia.org/wiki/Henri_Poincar%C3%A9
    "poincare",
    # Laura Poitras is a documentarian whose work advances truth and freedom of information. https://en.wikipedia.org/wiki/Laura_Poitras
    "poitras",
    # Tat’yana Avenirovna Proskuriakova was a Russian-American mathematician and programmer. https://en.wikipedia.org/wiki/Tatiana_Proskuriakova
    "proskuriakova",
    # Claudius Ptolemy - a Greco-Egyptian writer of Alexandria, known as a mathematician and astronomer. https://en.wikipedia.org/wiki/Ptolemy
    "ptolemy",
    # C. V. Raman - Indian physicist who won the Nobel Prize in 1930 for the Raman effect. https://en.wikipedia.org/wiki/C._V._Raman
    "raman",
    # Srinivasa Ramanujan - Indian mathematician and autodidact. https://en.wikipedia.org/wiki/Srinivasa_Ramanujan
    "ramanujan",
    # Sally Kristen Ride was an American physicist and astronaut. https://en.wikipedia.org/wiki/Sally_Ride
    "ride",
    # Dennis Ritchie - co-creator of UNIX and the C programming language. https://en.wikipedia.org/wiki/Dennis_Ritchie
    "ritchie",
    # Ida Rhodes - American pioneer in computer programming. https://en.wikipedia.org/wiki/Ida_Rhodes
    "rhodes",
    # Julia Hall Bowman Robinson - American mathematician renowned for computability and complexity theory. https://en.wikipedia.org/wiki/Julia_Robinson
    "robinson",
    # Wilhelm Conrad Röntgen - German physicist awarded the first Nobel Prize in Physics for discovering X-rays. https://en.wikipedia.org/wiki/Wilhelm_R%C3%B6ntgen
    "roentgen",
    # Rosalind Franklin - British biophysicist whose research was critical to understanding DNA. https://en.wikipedia.org/wiki/Rosalind_Franklin
    "rosalind",
    # Vera Rubin - American astronomer who pioneered work on galaxy rotation rates. https://en.wikipedia.org/wiki/Vera_Rubin
    "rubin",
    # Meghnad Saha - Indian astrophysicist known for the Saha equation. https://en.wikipedia.org/wiki/Meghnad_Saha
    "saha",
    # Jean E. Sammet developed FORMAC, the first widely used symbolic manipulation language. https://en.wikipedia.org/wiki/Jean_E._Sammet
    "sammet",
    # Carl Sagan - American astronomer and science popularizer. https://en.wikipedia.org/wiki/Carl_Sagan
    "sagan",
    # Mildred Sanderson - American mathematician best known for Sanderson's theorem. https://en.wikipedia.org/wiki/Mildred_Sanderson
    "sanderson",
    # Satoshi Nakamoto is the name used by the unknown person or group behind Bitcoin. https://en.wikipedia.org/wiki/Satoshi_Nakamoto
    "satoshi",
    # Abdus Salam - Pakistani theoretical physicist; 1979 Nobel Prize in Physics for electroweak unification. https://en.wikipedia.org/wiki/Abdus_Salam
    "salam",
    # Adi Shamir - Israeli cryptographer and co-inventor of RSA. https://en.wikipedia.org/wiki/Adi_Shamir
    "shamir",
    # Claude Shannon - The father of information theory and digital circuit design theory. https://en.wikipedia.org/wiki/Claude_Shannon
    "shannon",
    # Carol Shaw - originally an Atari employee, widely regarded as the first female video game designer. https://en.wikipedia.org/wiki/Carol_Shaw_(video_game_designer)
    "shaw",
    # Dame Stephanie "Steve" Shirley - Founded a software company employing women working from home. https://en.wikipedia.org/wiki/Steve_Shirley
    "shirley",
    # William Shockley co-invented the transistor. https://en.wikipedia.org/wiki/William_Shockley
    "shockley",
    # Lina Solomonovna Stern (or Shtern) was a Soviet biochemist and physiologist. https://en.wikipedia.org/wiki/Lina_Stern
    "shtern",
    # Françoise Barré-Sinoussi - French virologist and Nobel laureate who helped identify HIV. https://en.wikipedia.org/wiki/Fran%C3%A7oise_Barr%C3%A9-Sinoussi
    "sinoussi",
    # Betty Snyder - one of the original programmers of the ENIAC. https://en.wikipedia.org/wiki/Betty_Holberton
    "snyder",
    # Cynthia Solomon - Pioneer in artificial intelligence and educational computing. https://en.wikipedia.org/wiki/Cynthia_Solomon
    "solomon",
    # Frances Spence - one of the original programmers of the ENIAC. https://en.wikipedia.org/wiki/Frances_Spence
    "spence",
    # Michael Stonebraker is a database research pioneer and architect of Ingres and Postgres. https://en.wikipedia.org/wiki/Michael_Stonebraker
    "stonebraker",
    # Ivan Edward Sutherland - American computer scientist and Internet pioneer, father of computer graphics. https://en.wikipedia.org/wiki/Ivan_Sutherland
    "sutherland",
    # Janese Swanson developed the first Carmen Sandiego game. https://en.wikipedia.org/wiki/Janese_Swanson
    "swanson",
    # Aaron Swartz was influential in creating RSS, Markdown, Creative Commons, Reddit and more. https://en.wikipedia.org/wiki/Aaron_Swartz
    "swartz",
    # Bertha Swirles was a theoretical physicist who made contributions to early quantum theory. https://en.wikipedia.org/wiki/Bertha_Swirles
    "swirles",
    # Helen Brooke Taussig - American cardiologist and founder of paediatric cardiology. https://en.wikipedia.org/wiki/Helen_B._Taussig
    "taussig",
    # Valentina Tereshkova is a Russian engineer and cosmonaut; the first woman in space. https://en.wikipedia.org/wiki/Valentina_Tereshkova
    "tereshkova",
    # Nikola Tesla invented the AC electric system and many iconic gadgets. https://en.wikipedia.org/wiki/Nikola_Tesla
    "tesla",
    # Marie Tharp - American geologist and oceanic cartographer. https://en.wikipedia.org/wiki/Marie_Tharp
    "tharp",
    # Ken Thompson - co-creator of UNIX and the C programming language. https://en.wikipedia.org/wiki/Ken_Thompson
    "thompson",
    # Linus Torvalds invented Linux and Git. https://en.wikipedia.org/wiki/Linus_Torvalds
    "torvalds",
    # Youyou Tu - Chinese pharmaceutical chemist and educator who discovered artemisinin. https://en.wikipedia.org/wiki/Youyou_Tu
    "tu",
    # Alan Turing was a founding father of computer science. https://en.wikipedia.org/wiki/Alan_Turing.
    "turing",
    # Varahamihira - Ancient Indian mathematician who discovered trigonometric formulae. https://en.wikipedia.org/wiki/Var%C4%81hamihira
    "varahamihira",
    # Dorothy Vaughan was a NASA mathematician and computer programmer. https://en.wikipedia.org/wiki/Dorothy_Vaughan
    "vaughan",
    # Cédric Villani - French mathematician and Fields Medal laureate. https://en.wikipedia.org/wiki/C%C3%A9dric_Villani
    "villani",
    # Sir Mokshagundam Visvesvaraya - notable Indian engineer and statesman. https://en.wikipedia.org/wiki/M._Visvesvaraya
    "visvesvaraya",
    # Christiane Nüsslein-Volhard - German biologist and Nobel laureate. https://en.wikipedia.org/wiki/Christiane_N%C3%BCsslein-Volhard
    "volhard",
    # Marlyn Wescoff - one of the original programmers of the ENIAC. https://en.wikipedia.org/wiki/Marlyn_Meltzer
    "wescoff",
    # Sylvia B. Wilbur - British computer scientist who helped develop the ARPANET. https://en.wikipedia.org/wiki/Sylvia_Wilbur
    "wilbur",
    # Andrew Wiles - Notable British mathematician who proved Fermat's Last Theorem. https://en.wikipedia.org/wiki/Andrew_Wiles
    "wiles",
    # Roberta Williams did pioneering work in graphical adventure games. https://en.wikipedia.org/wiki/Roberta_Williams
    "williams",
    # Malcolm John Williamson - British mathematician and cryptographer. https://en.wikipedia.org/wiki/Malcolm_Williamson_(cryptanalyst)
    "williamson",
    # Sophie Wilson designed the first Acorn Micro-Computer and ARM instruction set. https://en.wikipedia.org/wiki/Sophie_Wilson
    "wilson",
    # Jeannette Wing - computer scientist and researcher on formal methods and security. https://en.wikipedia.org/wiki/Jeannette_Wing
    "wing",
    # Steve Wozniak invented the Apple I and Apple II. https://en.wikipedia.org/wiki/Steve_Wozniak
    "wozniak",
    # The Wright brothers, Orville and Wilbur, built the world's first successful airplane. https://en.wikipedia.org/wiki/Wright_brothers
    "wright",
    # Chen Ning Yang - Chinese-American physicist; Nobel Prize for parity violation. https://en.wikipedia.org/wiki/Chen_Ning_Yang
    "yang",
    # Chien-Shiung Wu - Chinese-American experimental physicist who made major contributions to nuclear physics. https://en.wikipedia.org/wiki/Chien-Shiung_Wu
    "wu",
    # Rosalyn Sussman Yalow - American medical physicist; co-winner of the 1977 Nobel Prize in Physiology or Medicine. https://en.wikipedia.org/wiki/Rosalyn_Sussman_Yalow
    "yalow",
    # Ada Yonath - an Israeli crystallographer and Nobel laureate. https://en.wikipedia.org/wiki/Ada_Yonath
    "yonath",
    # Nikolay Yegorovich Zhukovsky was a Russian scientist, mathematician and engineer. https://en.wikipedia.org/wiki/Nikolay_Zhukovsky_(scientist)
    "zhukovsky",
    # Jagadish Chandra Bose - Indian physicist, biologist, and botanist who did pioneering research on radio and microwave optics. https://en.wikipedia.org/wiki/Jagadish_Chandra_Bose
    "bose_jc",
    # Vikram Sarabhai - Indian space scientist and astronomer, founder of the Indian Space Research Organisation (ISRO). https://en.wikipedia.org/wiki/Vikram_Sarabhai
    "sarabhai",
    # Prafulla Chandra Ray - Indian chemist and industrialist, founder of Bengal Chemicals and Pharmaceuticals. https://en.wikipedia.org/wiki/Prafulla_Chandra_Ray
    "ray_pc",
    # Anna Mani - Indian meteorologist and physicist who made major contributions to solar radiation measurement. https://en.wikipedia.org/wiki/Anna_Mani
    "mani",
    # Kamal Ranadive - Indian microbiologist who made important discoveries about leukemia and cancer research. https://en.wikipedia.org/wiki/Kamal_Ranadive
    "ranadive",
    # Yash Pal - Indian space scientist and astrophysicist who contributed to the development of Indian satellite technology. https://en.wikipedia.org/wiki/Yash_Pal
    "yash_pal",
    # Demis Hassabis - British AI researcher and co-founder of DeepMind; 2024 Nobel Prize in Chemistry for AlphaFold. https://en.wikipedia.org/wiki/Demis_Hassabis
    "hassabis",
    # John Jumper - American AI researcher; 2024 Nobel Prize in Chemistry for developing AlphaFold2. https://en.wikipedia.org/wiki/John_Jumper
    "jumper",
    # Luc Montagnier - French virologist; co-discoverer of HIV, 2008 Nobel Prize in Physiology or Medicine. https://en.wikipedia.org/wiki/Luc_Montagnier
    "montagnier",
    # Jennifer Doudna - American biochemist; 2020 Nobel Prize in Chemistry for CRISPR gene editing. https://en.wikipedia.org/wiki/Jennifer_Doudna
    "doudna",
    # Emmanuelle Charpentier - French microbiologist; 2020 Nobel Prize in Chemistry for CRISPR gene editing. https://en.wikipedia.org/wiki/Emmanuelle_Charpentier
    "charpentier",
    # Roger Penrose - British physicist; 2020 Nobel Prize in Physics for black hole discoveries. https://en.wikipedia.org/wiki/Roger_Penrose
    "penrose",
    # Barry Marshall - Australian physician; 2005 Nobel Prize in Physiology or Medicine for Helicobacter pylori discovery. https://en.wikipedia.org/wiki/Barry_Marshall
    "marshall",
    # Robin Warren - Australian pathologist; 2005 Nobel Prize in Physiology or Medicine for H. pylori discovery. https://en.wikipedia.org/wiki/Robin_Warren
    "warren",
    # Shinya Yamanaka - Japanese physician; 2012 Nobel Prize in Physiology or Medicine for induced pluripotent stem cells. https://en.wikipedia.org/wiki/Shinya_Yamanaka
    "yamanaka",
    # Venkatraman Ramakrishnan - Indian-British structural biologist; 2009 Nobel Prize in Chemistry for ribosome studies. https://en.wikipedia.org/wiki/Venkatraman_Ramakrishnan
    "ramakrishnan",
    # Peter Higgs - British physicist; 2013 Nobel Prize in Physics for Higgs boson prediction. https://en.wikipedia.org/wiki/Peter_Higgs
    "higgs",
    # François Englert - Belgian theoretical physicist; 2013 Nobel Prize in Physics for Higgs mechanism theory. https://en.wikipedia.org/wiki/Fran%C3%A7ois_Englert
    "englert",
    # Donna Strickland - Canadian optical physicist; 2018 Nobel Prize in Physics for laser pulse amplification. https://en.wikipedia.org/wiki/Donna_Strickland
    "strickland",
    # Arthur Ashkin - American physicist; 2018 Nobel Prize in Physics for optical tweezers. https://en.wikipedia.org/wiki/Arthur_Ashkin
    "ashkin",
    # Kip Thorne - American physicist; 2017 Nobel Prize in Physics for gravitational wave detection. https://en.wikipedia.org/wiki/Kip_Thorne
    "thorne",
    # Andrea Ghez - American astronomer; 2020 Nobel Prize in Physics for black hole at Milky Way center. https://en.wikipedia.org/wiki/Andrea_Ghez
    "ghez",
    # Katalin Karikó - Hungarian-American biochemist; 2023 Nobel Prize in Physiology or Medicine for mRNA vaccine development. https://en.wikipedia.org/wiki/Katalin_Karik%C3%B3
    "kariko",
    # Drew Weissman - American immunologist; 2023 Nobel Prize in Physiology or Medicine for mRNA vaccine development. https://en.wikipedia.org/wiki/Drew_Weissman
    "weissman",
    # Georg Cantor - German mathematician; founder of set theory and the theory of infinite numbers. https://en.wikipedia.org/wiki/Georg_Cantor
    "cantor",
    # David Hilbert - German mathematician; formulated Hilbert's 23 problems. https://en.wikipedia.org/wiki/David_Hilbert
    "hilbert",
    # Bertrand Russell - British philosopher and mathematician; pioneer in mathematical logic. https://en.wikipedia.org/wiki/Bertrand_Russell
    "russell",
    # Kurt Gödel - Austrian mathematician and logician; famous for incompleteness theorems. https://en.wikipedia.org/wiki/Kurt_G%C3%B6del
    "godel",
    # Alonzo Church - American mathematician and logician; pioneer of computability theory and lambda calculus. https://en.wikipedia.org/wiki/Alonzo_Church
    "church",
    # Andrey Kolmogorov - Russian mathematician; founder of modern probability theory. https://en.wikipedia.org/wiki/Andrey_Kolmogorov
    "kolmogorov",
    # Geoffrey Hinton - British-Canadian cognitive psychologist; pioneer of deep learning, 2018 Turing Award. https://en.wikipedia.org/wiki/Geoffrey_Hinton
    "hinton",
    # Yann LeCun - French computer scientist; pioneer of convolutional neural networks, 2018 Turing Award. https://en.wikipedia.org/wiki/Yann_LeCun
    "lecun",
    # Yoshua Bengio - Canadian computer scientist; pioneer of deep learning, 2018 Turing Award. https://en.wikipedia.org/wiki/Yoshua_Bengio
    "bengio",
    # Herbert Simon - American polymath; 1978 Nobel Prize in Economics for bounded rationality and AI. https://en.wikipedia.org/wiki/Herbert_Simon
    "simon",
    # Marvin Minsky - American cognitive scientist; pioneer of artificial intelligence research. https://en.wikipedia.org/wiki/Marvin_Minsky
    "minsky",
    # Judea Pearl - American computer scientist; pioneer of Bayesian networks and causal reasoning in AI. https://en.wikipedia.org/wiki/Judea_Pearl
    "pearl",
    # Fred Hoyle - British astronomer and cosmologist; major contributions to stellar nucleosynthesis. https://en.wikipedia.org/wiki/Fred_Hoyle
    "hoyle",
    # Carl Woese - American microbiologist; discovered archaea and transformed the tree of life. https://en.wikipedia.org/wiki/Carl_Woese
    "woese",
    # Sydney Brenner - South African biologist; 2002 Nobel Prize in Physiology or Medicine. https://en.wikipedia.org/wiki/Sydney_Brenner
    "brenner",
    # Edvard Moser - Norwegian neuroscientist; 2014 Nobel Prize in Physiology or Medicine for grid cells discovery. https://en.wikipedia.org/wiki/Edvard_Moser
    "edvard_moser",
    # Bernardo Houssay - Argentine physiologist; 1947 Nobel Prize in Physiology or Medicine for endocrine regulation research. https://en.wikipedia.org/wiki/Bernardo_Houssay
    "houssay",
    # Luis Federico Leloir - Argentine biochemist; 1970 Nobel Prize in Chemistry for carbohydrate metabolism. https://en.wikipedia.org/wiki/Luis_Federico_Leloir
    "leloir",
    # Mario Molina - Mexican chemist; 1995 Nobel Prize in Chemistry for ozone depletion research. https://en.wikipedia.org/wiki/Mario_Molina
    "molina",
    # Osamu Shimomura - Japanese chemist; 2008 Nobel Prize in Chemistry for GFP discovery. https://en.wikipedia.org/wiki/Osamu_Shimomura
    "shimomura",
)
