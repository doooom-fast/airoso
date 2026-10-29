# GM proving grounds + every Michigan road course: research dossier

*Researched 2026-10-28 for a separate Opus build session. Research only: nothing here has been built,
and no geometry in this file is data (L1). This file is the input to a dossier, not a dossier that
has been approved.*

> **Where this file lives.** Researched in a `k10-track-agents` cloud session on 2026-10-28 and
> ported here the same day. Part D is the LOCATION-DOSSIER for the Milford Road Course, the ranked
> first build; Parts A–C are the GM and Michigan survey that produced that ranking. No
> `track.config.json` exists yet: Kevin approves Part D before any geometry is made.

## 0. Method, limits, and how to read the marks

- **Tooling reality.** WebFetch could not reach any host (DNS was blocked by session network policy
  for wikipedia, marketscreener and others). From bash, `overpass-api.de`, `nominatim`,
  `openstreetmap.org` and `tnmaccess.nationalmap.gov` were all unreachable. So every fact below comes
  from web-search result summaries, with each source URL cited. **No Overpass query, DEM tile, or
  imagery tile was actually pulled.** OSM coverage and lidar tiles are recorded as "expected" with
  the exact query or product to run, and the build session must run them.
- **Marks.** `[unverified]` means a claim was found but not corroborated, or the source is weak (a
  forum, an auto-generated aggregator, or a single mirror). `[conflict]` means sources disagree, and
  every value is listed. `[derived]` means I computed it from sourced inputs, with the formula shown.
  `[not found]` means I searched and found nothing, which is not the same as "doesn't exist".
- **Rule kept:** no length, corner count, or layout is stated as fact unless a source states it.
  Where sources disagree, the build has to take the number from the imagery trace, never from this
  file.

---

# Part A: General Motors test tracks, worldwide

## A1. Inventory: current and historical

| Site | Location (lat/lon where sourced) | Years / status / owner | Circuits on site (as published) | Sources |
|---|---|---|---|---|
| **Milford Proving Ground (MPG)** | Milford & Brighton Twps, MI. 42.5836 N, 83.6844 W (Wikipedia infobox via search). 3300 General Motors Rd, Milford MI 48380 | Opened **25 Sep 1924**. **Active**, GM-owned. About 4,000 acres, with about 132 to 150 mi of roads `[conflict: 132 / 131+16 gravel / ~150]` | Milford Road Course, 4.5-mi Circle Track, Black Lake VDTA, N/S Straightaway, Ride & Handling / N&V loop, Belgian Block loop, Seven Sisters, noise roads, grades, dirt roads. See A2 | [GM 20 facts](https://news.gm.com/home.detail.html/Pages/news/us/en/2024/sep/0925-mpg100-20-facts.html), [GM facility page](https://gm.com/company/facilities/milford-proving-ground), [WP](https://en.wikipedia.org/wiki/General_Motors_proving_grounds), [GM Authority 2024](https://gmauthority.com/blog/2024/09/interesting-facts-and-figures-about-gms-milford-proving-ground/) |
| **Desert Proving Ground – Yuma (DPG-Y)** | Inside US Army Yuma Proving Ground, AZ. Coordinates `[not found]` | Fully online **July 2009**. GM co-built and leases it (50-yr lease + 50-yr option). **Status `[unverified]`:** Nov-2024 reporting covers 33 layoffs, under a "will close 2 Arizona proving grounds" headline | 3.5-mi Circle Track (3 lanes), 1.4-mi straight, 3.1-mi Ride Road, 1,000 ft × 1,000 ft Dynamics Pad, off-road PG added 2016. See A3 | [Reliable Plant 2009](https://www.reliableplant.com/Read/18985/gm-opens-yuma-proving-ground-in-arizona-desert), [AutoChannel 2009](https://www.theautochannel.com/news/2009/07/22/471063.html), [army.mil](https://www.army.mil/article/228537/general_motors_celebrates_10_years_at_yuma_proving_ground), [AZFamily 2024](https://www.azfamily.com/2024/11/15/rural-arizona-hit-by-automakers-layoffs-what-know-about-gm-stellantis/), [GM Authority 2016](https://gmauthority.com/blog/2016/11/general-motors-develops-new-off-road-proving-grounds-in-yuma-arizona/) |
| **Desert Proving Ground – Mesa** (historical) | Mesa, AZ (now Eastmark). Coordinates `[not found]` | **1953 to 2009**, closed and moved to Yuma. Southern third sold 2004 (Levine / Pacific Proving). Northern 5 sq mi sold 2006 to DMB for $265 M, renamed Eastmark in 2012 | "Banked test track where the minimum speed was 90 mph". 74 to 85 mi of track/roadway `[conflict]`. **Trackways still visible** in the southern portion (Pecos Rd to Bell Bank Park) per 2022 | [HistoricAerials](https://blog.historicaerials.com/?p=82), [AZ Republic timeline](https://www.pressreader.com/usa/the-arizona-republic/20130512/282003259940695), [EVT Business 2022](https://issuu.com/timespub/docs/evtbizz_0605) |
| Phoenix hot-weather site (historical) | Central Phoenix | 1937, GM's earliest Arizona site `[unverified: secondary, Flickr quoting AZ Republic]` | `[not found]` | [Flickr](https://www.flickr.com/photos/blazenhoff/57816955) |
| **Kapuskasing Cold Weather Development Centre** | Kapuskasing, ON | About 51 years. **Closure announced Oct 2024** | 272 acres, 3.6 km test track, 30 cold cells to −45 °C | [CTV](https://northernontario.ctvnews.ca/after-51-years-gm-closes-cold-weather-testing-facility-in-kapuskasing-ont-1.7081833) |
| **Holden Lang Lang PG** | Lang Lang, VIC, Australia | 1957. **Sold Sept 2020** to VinFast/VinGroup, later resold to a defence contractor | 877 ha, 44 km sealed + unsealed roads, **4.7 km high-speed bowl** | [CarsGuide](https://www.carsguide.com.au/car-news/holdens-lang-lang-proving-ground-sold-to-vietnamese-car-maker-vinfast-80614), [GoAuto](https://goauto.com.au/news/general-news/corporate/lang-lang-proving-ground-sold/2020-09-09/83643.html), [JustCars resale](https://www.justcars.com.au/news-and-reviews/former-holden-proving-ground-sold-again/1089515) |
| **Opel Test Center Dudenhofen** | Rodgau-Dudenhofen, Hesse, DE | 1964 or 1966 `[conflict]`. Left GM with the Opel sale to PSA (Aug 2017). Segula leased and ran it 2018 to Oct 2025, then went insolvent. **TRIWO operates it from June 2026.** Owner is Opel (Stellantis) | About 40 km of tracks incl. **4.8 km high-speed oval** `[unverified: single source]` | [NewMobility 2025](https://newmobility.news/2025/10/29/opel-forced-to-shut-down-german-testing-facilities-300-jobs-lost/), [AMS 2026](https://www.auto-motor-und-sport.de/verkehr/testzentrum-dudenhofen-startet-neu-opel-kann-wieder-autos-testen/), [Opel SG](https://opel.com.sg/what-is-special-at-dudenhofen) |
| **Guangde Proving Ground** | Guangde County, Anhui, CN | Opened **22 Sep 2012**. GM + SAIC + Shanghai GM + PATAC | 5.67 km², 60 km of roads. Areas: oval, VDA, long straight, R&H loop, noise road, durability, corrosion, hill area | [GM Authority 2012](https://gmauthority.com/blog/2012/09/say-hello-to-gms-new-proving-ground-in-china/), [Autoblog](https://www.autoblog.com/2012/09/24/gm-opens-chinas-largest-proving-ground/) |
| **Cheongna Proving Ground** | Incheon FEZ, KR (about 10 km from Bupyeong) | Completed Sept 2007 by GM Daewoo. Active (GM Korea) | Handling + NVH track, climate wind tunnel, 600 m × 60 m active-safety road | [JoongAng](https://www.koreajoongangdaily.com/business/gm-uses-korea-as-launching-pad-to-bric-nations/11553257), [CarGuide PH](https://www.carguide.ph/2022/02/check-out-chevrolets-new-active-safety.html?m=1), [Asiae 2025](https://www.asiae.co.kr/en/article/2025121509482667914) |
| **Cruz Alta PG** | Indaiatuba, SP, BR | 1974. Active | 16 test tracks, about 44 km `[conflict on count/length]` | [Comprecar](https://www.comprecar.com.br/revista/campo-de-provas-da-gm-completa-40-anos), [GM Authority 2019](https://gmauthority.com/blog/2019/08/gm-brazil-proving-ground-celebrates-45th-anniversary/), [MarkLines](https://www.marklines.com/en/news/229073) |
| Mexico PG | Cupuán del Río, Michoacán | 2006. **Largely abandoned by 2011** (security) | Circle track + off-road courses | [WP via search](https://en.wikipedia.org/wiki/General_Motors_proving_grounds) |
| Arjeplog winter site | Arjeplog, SE | Listed as a heading only `[unverified]` | `[not found]` | [WP via search](https://en.wikipedia.org/wiki/General_Motors_proving_grounds) |
| Nürburgring | Nürburg, DE | **No GM-owned test centre found** `[not found]`. The Meuspath centre in results is Aston Martin's (2008). GM's Nordschleife work is a development programme: 31 combined visits, 2025 Corvette records Z06 6:49.275 / ZR1 6:50.763 / ZR1X 7:11.826 | The Nordschleife itself is the reference the Milford Road Course imitates | [GM News 2025](https://news.gm.com/home.detail.html/Pages/topic/us/en/2025/jul/0731-Nurburgring.html), [evo (Aston)](https://www.evo.co.uk/news/evonews/217416/ams_new_test_centre.html) |
| Spring Mountain Motor Resort | Pahrump, NV | **Not GM-owned.** Hosted the Ron Fellows Corvette Owners School (C7 programme ended 31 Dec 2020, C8 resumed June 2020) and the Cadillac V-Performance Academy. Current status `[unverified]` | Club circuit, not GM's | [SMMR newsletter 2020](https://www.springmountainmotorsports.com/news/newsletter/club-spring-mountain-news-august-2020/), [GM Authority 2020](https://gmauthority.com/blog/2020/06/c8-corvette-owners-school-reopens-for-classes/) |
| Warren Technical Center | Warren, MI | Engineering campus | **No test track found** `[not found]` | — |
| Kettering Univ. GM Mobility Research Center | Flint, MI | University-run, GM-named | Autonomous test track on former vacant land | [TechCrunch](https://techcrunch.com/?p=1400007) |

**A misattribution to fix.** The Wikipedia proving-grounds page's list of "3.5 mi Circle Track (3
lanes), 1.4 mi straight, 3.1 mi Ride Road" matches the **Yuma 2009 press kit** word for word, not
Milford ([AutoChannel](https://www.theautochannel.com/news/2009/07/22/471063.html),
[WP](https://en.wikipedia.org/wiki/General_Motors_proving_grounds)). Several fan pages copy it into
Milford fact lists. Milford's circle track is **4.5 mi, 5 lanes**. Don't let the 3.5 mi figure into a
Milford config.

## A2. Milford Proving Ground: deep dive

### A2.1 Site envelope

| Fact | Value | Source |
|---|---|---|
| Boundary roads | **Hickory Ridge Rd (E), Pleasant Valley Rd (W), Commerce Rd (N)**. South edge `[not found]` | [GM facility handbook (Brencal)](https://www.brencal.net/wp-content/uploads/2014/07/HBMilford.pdf) |
| Townships / counties | **Milford Twp (Oakland Co.) + Brighton Twp (Livingston Co.)**. The site straddles the county line, so both counties' lidar is needed | [Brencal handbook](https://www.brencal.net/wp-content/uploads/2014/07/HBMilford.pdf) |
| Original terrain | Nicknamed **"The Bluffs"** for **267 ft** of site relief | [GM Authority 2024](https://gmauthority.com/blog/2024/09/interesting-facts-and-figures-about-gms-milford-proving-ground/) via search |
| Growth | 1,125 acres and 5.5 mi of road in 1924, now about 4,000 acres | [Hagerty](https://www.hagerty.com/media/news/gms-milford-proving-grounds-celebrates-its-centennial/), [GM Authority 2021](https://gmauthority.com/blog/2021/09/gm-milford-proving-ground-turns-97-years-old-today/) |
| Airspace | A no-fly zone limits overhead photography. Satellite imagery is **not known to be blurred** `[not found: no source reports blurring]` | [SlashGear](https://www.slashgear.com/2042824/general-motors-milford-proving-grounds-history-details/) via search |
| Heritage | Highway guardrail was developed at Milford, so guardrail rather than concrete is the period-correct edge treatment `[verify per corner in video]` | [WMMQ](https://wmmq.com/ixp/690/p/gm-proving-grounds-highway-guardrails/) |

### A2.2 Every drivable loop found

| Loop | Length | Width / lanes | Banking / grade | Surface | Built | Notes | Sources |
|---|---|---|---|---|---|---|---|
| **Milford Road Course (MRC, "Lutzring")** | **2.9 mi / 4.7 km** (GM). "About 3 mi" in one source | `[not found]`. Measure from imagery | **135 ft (41 m) elevation change** (SAE 2005 design paper). "Plunges 41 m from hilltop to trough" (carsales). 120 ft in one forum `[conflict, minority]` | Asphalt `[unverified: inferred from photos/videos, no text source]` | 2003 start, about 2004 complete | **17 turns** (GM releases) / **18** (forum) / **20, "configurable closed course"** (SAE paper, carsales) `[conflict]`. Corners modelled on famous circuits, some from the Nürburgring incl. a **Carousel** simulation. "Very tight curb-filled corners". Long straight **>150 mph** | [GM 20 facts](https://news.gm.com/home.detail.html/Pages/news/us/en/2024/sep/0925-mpg100-20-facts.html), [TRID: "Design of the Milford Road Course"](https://trid.trb.org/View/1803993), [carsales ZR1](https://www.carsales.com.au/editorial/details/chevrolet-corvette-zr1-14336/), [LSX video](https://www.lsxmag.com/news/video-gms-milford-proving-grounds/), [RK Motors](https://www.rkmotors.com/blog/Milford-Turns-97), [camaro5](https://www.camaro5.com/forums/showthread.php?p=6372265) |
| **Circle Track** | **4.5 mi / 7.2 km** | **5 lanes**, posted speeds rising toward the outer lane | Banked "**concrete parabolic curve**". Each lane can be driven hands-off at its posted speed. **Angle not published.** `[derived]` neutral-steer bank θ = atan(v²/gr), with r = 7,242 m / 2π ≈ 1,153 m: **≈10° at 100 mph, ≈14° at 120 mph.** Parabolic means steeper toward the outside | "Dolomite" concrete | **1964** (GM centennial) | Outer lane posted "100+ mph" or "120 mph" `[conflict]`. A 1950s self-driving Chevy followed a cable buried in the circular track, which suggests an earlier circular track `[unverified lineage]` | [PEA Group](https://peagroup.com/what-we-do/our-work/general-motors-circle-track/), [WP](https://en.wikipedia.org/wiki/General_Motors_proving_grounds), [GTPlanet](https://www.gtplanet.net/forum/threads/general-motors-milford-proving-grounds.315800/), [GM Authority 2024](https://gmauthority.com/blog/2024/09/interesting-facts-and-figures-about-gms-milford-proving-ground/) |
| **Black Lake / VDTA** | Pad: **67 acres (≈270,000 m²)**, "51 football fields" (or "59") `[conflict]` | Open pad | Flat | Blacktop (one source says concrete `[conflict]`) | `[not found]` | Inside the Circle Track. **Semicircular run-up tracks at each end** | [WP](https://en.wikipedia.org/wiki/General_Motors_proving_grounds), [GM Authority 2024](https://gmauthority.com/blog/2024/09/interesting-facts-and-figures-about-gms-milford-proving-ground/) |
| **North/South Straightaway** | About **3 mi**, 3 lanes. One forum gives 6.225 mi total with two 2.5-mi straights `[unverified]` | 3 lanes | — | `[not found]` | **1955** | Top-speed tests. Jim Mero gave journalists ZR1 rides "on the Proving Grounds 3 mile straight" | [Corvette Club UK](https://www.corvetteclub.org.uk/threads/did-you-know-this.6803/), [Mero media](https://jimmero.com/videos-interviews-podcasts/) |
| **Ride & Handling / Noise & Vibration loop** | `[not found]` | `[not found]` | Varied surfaces and turns | Mixed | — | Whether it "encloses" the Circle Track or is "enclosed by" it is `[conflict]`. Grouped with the **Fenn Holden area** (named for the first PG director) and "the Oval track" | [WP](https://en.wikipedia.org/wiki/General_Motors_proving_grounds), [MECF](https://www.midenginecorvetteforum.com/forum/general-forums/wheeled-transportation-section/336074-gm%E2%80%99s-milford-proving-ground-the-milford-road-course) |
| "Oval track" | **3.8 mi** `[unverified: one summary]` | — | — | — | — | Distinct from the Circle Track? `[unverified]` | [MarketScreener / GM 20 facts summary](https://news.gm.com/home.detail.html/Pages/news/us/en/2024/sep/0925-mpg100-20-facts.html) |
| **Belgian Block loop** | `[not found]` | — | — | Rough block "brick" | — | Driven for entire days in durability runs | [GM Authority 2014](https://gmauthority.com/blog/2014/10/general-motors-celebrates-90-years-of-vehicle-testing-and-abuse-at-its-milford-proving-grounds/), [Autoweb](https://www.autoweb.com/general-motors-milford-proving-grounds-90th-birthday) |
| **Seven Sisters** | **About 2,000 ft** | **One lane, bidirectional**, one car at a time | **Superelevation 1.5–7 %** | Asphalt (rebuilt) | Rebuilt fall 2011 | Seven tight curves, some level, some banked. Transient lateral load testing | [Iafrate Construction](https://iafrate.com/portfolio-items/gm-milford-seven-sisters/), [WP](https://en.wikipedia.org/wiki/General_Motors_proving_grounds) |
| Interior Noise Road, Noise Pass-by facility | `[not found]` | — | — | — | — | Listed on WP with "citation needed" | [WP](https://en.wikipedia.org/wiki/General_Motors_proving_grounds) |
| Grades / "steep hills", paved + dirt roads | `[not found]` | — | "Misc. grades" | Paved + dirt | — | No named hill route found | [GM centennial](https://news.gm.com/home.detail.html/Pages/news/us/en/2024/sep/0925-mpg100-employees.html) |
| Durability features | — | — | — | — | — | Pothole drives, chatter bumps, twist ditches, speed bumps | [Autoweb](https://www.autoweb.com/general-motors-milford-proving-grounds-90th-birthday) |
| Off-road / truck course | `[not found]` | — | — | — | — | No Milford-specific off-road course found. GM's dedicated off-road PG is at Yuma (2016) | [GM Authority 2016](https://gmauthority.com/blog/2016/11/general-motors-develops-new-off-road-proving-grounds-in-yuma-arizona/) |

### A2.3 Media that gives corner-by-corner character on the MRC

| Ref | What it shows | URL |
|---|---|---|
| Jim Mero, ZR1 hot lap at MPG | Engineer-driven lap (YouTube) | https://www.youtube.com/watch?v=tNRWvk5nMu0 |
| Capital City Corvette Club | In-car 2009 ZR1 with Mero "at the Lutz Ring otherwise known as Milford Road Course" | https://cccorvette.org/share.html |
| Autoweek / Corvette Blogger 2013 | Full lap of the MRC in a 2014 Stingray | https://www.corvetteblogger.com/2013/08/05/video-take-a-lap-around-the-milford-proving-grounds-in-the-2014-corvette-stingray/ |
| CBS Sunday Morning 2024 | 2025 ZR1 with chief engineer Tony Roma, 170 mph "on a long straight" (segment at 3:19). **Probably the N/S straight, not the MRC** `[unverified]` | https://www.corvetteblogger.com/2024/09/23/video-2025-corvette-zr1-goes-170-mph-and-does-360s-at-the-milford-proving-ground/ |
| Montoya ZR1 ride-alongs 2010 | Shaky passenger footage | https://www.motorauthority.com/news/1048511_video-juan-pablo-montoya-thrashes-corvette-zr1-at-milford |
| GM video: Camaro Z/28 vs Boss 302 | **Lap-time anchor: Z/28 1:53.71, Boss 302 1:59.05** "at Milford" | https://www.lsxmag.com/news/video-camaro-z28-vs-boss-302-at-the-milford-proving-grounds |
| ZL1 1LE | 1LE about 3 s faster than ZL1. 10-speed about 0.5 s faster than the manual | https://www.torquenews.com/106/ride-along-2017-camaro-zl1-milford-proving-grounds, https://topgear.com.my/news/the-chevy-camaro-zl1-1le-now-gets-a-ten-speed-gearbox |
| GM Authority 2015 / 2014 site videos | Tour of the different tracks | https://gmauthority.com/blog/2015/01/a-look-at-the-different-tracks-of-the-90-year-old-milford-proving-ground/, https://gmauthority.com/blog/2014/01/an-in-depth-look-at-the-milford-proving-grounds-video/ |
| Gadgetopia "The GM Report" | A Google Maps view of MPG **annotated with facility names** by a visitor. Fastest way to locate the MRC in imagery | https://archive.gadgetopia.com/post/6095/ |
| Wikimedia Commons | Free-licence photo of the grounds | https://commons.wikimedia.org/wiki/File:GM_proving_ground_Milford.JPG |
| Cadillac review (crest note) | "Aim for the left edge of the approaching rise… the chassis unloads over the crest just as it hits the apex". Corner identity `[unverified]`, attribution `[unverified]` | https://ls1tech.com/forums/automotive-news-media-press/1676199-edmunds-full-test-2014-cadillac-cts-vsport-twin-turbo.html |

**MRC average-speed sanity** `[derived]`: 2.9 mi in 113.71 s (Z/28) is **≈91.8 mph (≈148 km/h)
average**. That is a fast, flowing course, Road-America-like in average speed, not a tight handling
loop.

### A2.4 Data reality for Milford

| Input | Status | Source / how to get |
|---|---|---|
| **Published track map** | **None found** `[not found]`. GM has never released an MRC layout diagram that search could find | — |
| **OSM inside the fence** | **Unknown.** Overpass was unreachable. For comparison, Ford's Romeo PG **does** have a `highway=raceway` way named "Proving Ground" ([way 508396678](https://www.openstreetmap.org/way/508396678)) | Run the query in §Opus handoff step 2 |
| **Public aerial** | **USDA NAIP** (public domain, georeferenced, 0.6 m class `[unverified for MI vintages]`). Google/Bing/ESRI basemaps, with no report of blurring. Michigan **MiSAIL 12-inch** imagery is **view-only, not downloadable** | [MiSAIL](https://www.michigan.gov/dtmb/services/maps/misail) |
| **Lidar, Oakland Co. side** | **OC 2017 lidar, QL2, 19.6 cm NVA, ~907 sq mi** (USGS LBS 1.2). Also USGS 3DEP **MI_31County_2016 / MI_31Co_Oakland_2016** | [Oakland open data](https://accessoakland.oakgov.com/datasets/oc-2017-lidar-image-service/about), [BTAA](https://geo.btaa.org/catalog/9ded3291eb454ab69bc3620703c5d158), [USGS rockyweb](https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/metadata/MI_31County_2016_A16/MI_31Co_Oakland_2016/reports/) |
| **Lidar, Livingston Co. side** | **NRCS 30-County MI lidar 2016–17**, collected **2017-12-02 → 2018-04-22**, QL2 | [NOAA InPort](https://www.fisheries.noaa.gov/inport/item/55315) |
| Statewide | Michigan QL2 collected 2015–2020, downloadable from The National Map. Statewide 3DEP QL2 is complete | [MiSAIL](https://www.michigan.gov/dtmb/services/maps/misail), [USGS FS 2024-3031](https://pubs.usgs.gov/publication/fs20243031/full) |
| **Lidar vs build date** | The MRC (2003–04) is **older than both lidar flights**, so the bare-earth DEM shows the as-built course. The Circle Track (1964) and the straight (1955) are too | — |

### A2.5 Legal and access reality

- MPG is a **private, secured GM facility** with a no-fly zone. No public driving, no published
  map. Reconstruction can only be **imagery + public lidar + public media**. Public-domain
  NAIP and 3DEP carry no restriction on use.
- **Naming and branding:** per the Artifact/publishing rules and plain sense, a build must **not
  carry GM marks, logos or the "General Motors" name as branding**, and must not present itself as
  GM-endorsed. A neutral slug and name (for example `milford_road_course`, "Milford Road Course
  (unofficial reconstruction)") is the safe default. **Whether it is ever distributed is Kevin's
  call.** REALISM §3's clean-room rule already keeps shipped content to owned assets.
- If Kevin has a GM relationship that could supply an official centerline, survey or corner list,
  that **supersedes everything in this file**. Ask; don't assume.

## A3. Desert Proving Ground – Yuma (depth-lite)

| Fact | Value | Source |
|---|---|---|
| Opened | July 2009, with the US Army. GM co-built and leases it | [AutoChannel](https://www.theautochannel.com/news/2009/07/22/471063.html), [Reliable Plant](https://www.reliableplant.com/Read/18985/gm-opens-yuma-proving-ground-in-arizona-desert) |
| Size | 2,400-acre inner facility, 24-acre campus, 98,000 ft² of buildings, 40 mi of roadway. One press-kit line says "87 lane-miles of 12 ft test tracks & roads" | same, [WP](https://en.wikipedia.org/wiki/General_Motors_proving_grounds) |
| Circle Track | **3.5 mi, 3 lanes** (press kit). Army/DVIDS gives "3½-mile circular" while another Army line says "4½-mile high speed paved oval … heaviest vehicles in the Army inventory" `[conflict]`. The 4.5 figure may be the Army's own oval | [AutoChannel](https://www.theautochannel.com/news/2009/07/22/471063.html), [DVIDS](https://www.dvidshub.net/news/347772/general-motors-celebrates-10-years-yuma-proving-ground) |
| Straight | 1.4 mi | press kit |
| Ride Road | 3.1 mi | press kit |
| Dynamics pad | **1,000 ft × 1,000 ft (≈1,000,000 ft²)**. Milled and resurfaced 2013, mill-and-overlay design 2017 | [PEA Group](https://peagroup.com/what-we-do/our-work/general-motors-vehicle-dynamics-test-area/) |
| Road course | **None published** `[not found]` | — |
| Off-road | Off-road PG added 2016 | [GM Authority 2016](https://gmauthority.com/blog/2016/11/general-motors-develops-new-off-road-proving-grounds-in-yuma-arizona/) |
| Status | Nov 2024: 33 layoffs, reported as closure `[unverified completion]` | [AZFamily](https://www.azfamily.com/2024/11/15/rural-arizona-hit-by-automakers-layoffs-what-know-about-gm-stellantis/) |
| Build value | Low. A 3.5-mi circle and a pad are not a drive. It sits inside a military reservation with no published circuit | — |

---

# Part B: Every road course and racing circuit in Michigan

Classification key: **CLUB** = public club/track-day circuit · **PG** = manufacturer/supplier proving
ground (private) · **AV** = automated-vehicle testbed · **STREET** = temporary street circuit ·
**HIST** = defunct · **OVAL** = excluded, noted only.

## B1. Master table

| # | Venue | Class | Location (lat/lon if sourced) | Length / turns | Elev. change | Width | Surface | Layouts | Ownership / access | OSM | Lidar | Existing AC mod | Sources |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **GingerMan Raceway** | CLUB | Geneva Twp, Van Buren Co., near South Haven. **42.40861, −86.13806** | **2.14 mi / 11 T** (WP). 2.21 mi after the 2009–10 T10 extension, 1.88 mi original `[conflict]` | "Slight". T10B drops downhill `[no figure]` | **36 ft** (LapMeta) / 11 m (AW) | Asphalt, repaved 2015 | 10A original + 10B extended, CW + CCW | Private, public track days. Built 1995, first season 1996. Designer Alan Wilson | Expected `[unverified]` | Van Buren in MI 2015 13-county (Sanborn, Dec 2014–Fall 2015) | **Yes:** shin956/cyruscloud rF2 conversion v1.0 (2023), 2 layouts + 2 reverse, AI, 28 pits | [WP](https://en.wikipedia.org/wiki/Gingerman_Raceway), [GRIDLIFE](https://grid.life/gingerman-driver-resources), [LapMeta](https://www.lapmeta.com/en/track/variation/103), [Overtake](https://www.overtake.gg/downloads/gingerman-raceway.62436/), [AW](https://www.assettoworld.com/track/gingerman-raceway-full-forward), [Allegan/13-co lidar](https://noaa-nos-coastal-lidar-pds.s3.amazonaws.com/laz/geoid18/8520/supplemental/mi2015_allegan_m8520_lidar_report.pdf) |
| 2 | **Grattan Raceway Park** | CLUB | Grattan Twp, Kent Co. 7201 Lessiter Rd, Belding. **43.09667, −85.38333** (TopoQuest, 882 ft MSL) | **2.0 mi**. 10 T (SCCA, The Drive) / 12–13 T (RRW, LapMeta) `[conflict: numbering varies by map vintage]`. LapMeta CW variant 1.81 mi | **≈31 m** (LapMeta). 62 m on another page `[conflict]` | **40 ft** | Asphalt | Main CW. Motorcycle + kart use | Faasen family since about 1960–61. **For sale ($10–15 M), still operating** | Expected `[unverified]` | Kent: NRCS 30-county, late 2017–spring 2018 `[unverified dates]` | **Patreon only:** EKO Sim-Racing "Grattan V1.0", Feint Visuals/Shadow's Garage v0.8 (locked). Quality `[unverified]` | [SCCA](https://www.scca.com/locations/1981668-grattan-raceway), [The Drive](https://www.thedrive.com/news/who-can-save-this-historic-michigan-race-track-with-a-price-of-15-million), [racingcircuits](https://racingcircuits.info/north-america/usa/grattan-raceway.html), [RRW sale](https://roadracingworld.com/news/grattan-raceway-park-is-for-saleand-it-has-been-for-years), [RRW obit](https://roadracingworld.com/?p=13758), [TopoQuest](https://topoquest.com/place-detail.php?id=2570236), [LapMeta](https://lapmeta.com/en/track/variation/136), [EKO](https://www.patreon.com/posts/grattan-v1-0-is-123241931), [Feint](https://www.patreon.com/posts/grattan-raceway-117268690) |
| 3 | **Waterford Hills Road Racing** | CLUB | Independence Twp, Oakland Co. 4770 Waterford Rd, Clarkston (Oakland County Sportsmen's Club). **42.70925, −83.39083** `[single mirror]` | **1.4212 mi** (WP mirror) / 1.5 mi (most) `[conflict]`. 8 T / 12 T `[conflict]` | **56 ft / 17 m** (LapMeta) | `[not found]` | Asphalt, major reconstruction and repave about 2018–19 `[inferred date]` | Single. Layout unchanged since 1958 | Club-owned (WHRRI). Founded 1958, **oldest in MI** | Expected `[unverified]` | Oakland OC 2017 QL2 | **Yes:** adamcyan1624 "Waterford Hills" (Overtake). Reviewers say layout and elevation are accurate, **pre-repave**, "first version" | [racingcircuits](https://racingcircuits.info/north-america/usa/waterford-hills.html), [michigan.org](https://www.michigan.org/property/waterford-hills-road-racing-course), [LapMeta](https://lapmeta.com/en/track/variation/119), [Overtake](https://overtake.gg/downloads/waterford-hills.32663/reviews), [thread](https://www.overtake.gg/threads/waterford-hills.182991/) |
| 4 | **Michigan International Speedway road courses** | CLUB (oval venue) | Cambridge Twp (Lenawee Co. `[unverified]`), near Brooklyn. **42.06639, −84.24139** | **Infield 1.9 mi** (active, limited use). **Combined/exterior 3.1–3.31 mi** (1968 → 1973/1994 `[conflict on end]`). Turns `[not found]`. A 1.4-mi west infield loop is used for track days | Flat site `[unverified]`. Oval banking 18° in the turns, straights 12°/5° or 5°/2° `[conflict]` | Oval 73 ft in the turns, 45 ft on the straights | Asphalt | Infield, exterior, combined (**designed by Stirling Moss**) | ISC/NASCAR-owned. Last infield race 1984 (IMSA GTP lap record 1:06.060, Whittington, March 84G). Police and OEM testing | Expected for the oval `[unverified for infield]` | Lenawee `[unverified]` | **Oval only** (`aa_michigan` by 13x). **No road-course mod found** | [WP](https://en.wikipedia.org/wiki/Michigan_International_Speedway), [MIS track facts](https://www.mispeedway.com/track-facts/), [Motor Sport](https://www.motorsportmagazine.com/database/circuits/michigan/), [Jayski](https://www.jayski.com/nascar-tracks-news/michigan-international-speedway/), [Xtreme](https://www.thextremexperience.com/?p=10463), [AW oval](https://www.assettoworld.com/track/michigan-speedway) |
| 5 | **M1 Concourse, Champion Motor Speedway** | CLUB (private members) | Pontiac, Oakland Co. Coordinates `[not found]` | **1.5 mi / 2.41 km, 9 T** | 25 ft vs 51 ft `[conflict]` | `[not found]` | Asphalt | CW + CCW | Private club, OEM testing. Designer Martyn Thake. About 2016 `[unverified date]` | Expected `[unverified]` | Oakland OC 2017 (check against the build date) | **Yes, laser-scanned:** SIM TRAXX (CW1/CCW1, 2.4 km, AI, 16 pits) plus a newer "ultimate" release | [LapMeta](https://lapmeta.com/ja/track/variation/150), [Brake & Front End](https://www.brakeandfrontend.com/federal-mogul-motorparts-unveils-new-m1-concourse-performance-track-name-and-logo/), [AW](https://www.assettoworld.com/track/m1-concourse-champion-motor-speedway-cw1), [SIM TRAXX](https://www.patreon.com/posts/sunday-cruising-140504060) |
| 6 | **Motorsports Gateway Howell (South Circuit)** | CLUB (private members) | Howell, Livingston Co. Between D-19/Michigan Ave and Lucy Rd, off I-96. Coordinates `[not found]` | **1.7 mi / 13 T** (Oct 2025). Earlier 1.75 mi / 15 T `[conflict: layout changed in build]` | **≈144 ft** | **40 ft** (Racer 2024) | Asphalt, paved 2024–25 | Built to split into two simultaneous circuits. North circuit is a later phase | Private. **Soft-opened Oct 2025.** Designer Driven International | Unlikely yet | **NRCS 2017–18 lidar is from before the earthworks (2023)** | **None found** | [DBusiness](https://www.dbusiness.com/daily-news/motorsports-gateway-in-howell-opens-1-7-mile-13-turn-track-circuit/), [WHMI](https://www.whmi.com/news/article/48858), [Racer](https://racer.com/2024/09/27/motorsports-gateway-howell-completes-paving-on-south-circuit/), [MG update](https://www.motorsportsgateway.com/news/september-2024-construction-update-motorsports-gateway-howell-reaches-major-milestones-with-south-circuit-paving) |
| 7 | **GM Milford Road Course** | PG | See A2 | 2.9 mi / 17–20 T | 41 m | `[not found]` | Asphalt `[unverified]` | "Configurable" (SAE) | GM private | Unknown | OC 2017 + NRCS 2017–18 | **None found** | Part A |
| 8 | **Stellantis Chelsea PG** | PG | Sylvan Twp, Washtenaw Co. 3700 S M-52, Chelsea | 4.71-mi high-banked oval (built 1953, rebuilt 2007, 30–140 mph hands-off). **"Small road course with several hairpin turns"**, length `[not found]`. Ride road, handling road | — | — | — | — | Private, 3,850 acres, about 95 (lane-)mi of roads | `[unverified]` | Washtenaw `[unverified]` | None found | [Auto123](https://www.auto123.com/en/news/amp/chelsea-proving-grounds-a-chrysler-smorgasbord/57161/), [Stellantis PDF](https://embargoed.stellantisnorthamerica.com/pdf.do?id=7199), [Autoblog](https://www.autoblog.com/2007/09/17/chrysler-proving-ground-high-speed-oval-re-opens-after-rebuild/), [Just Auto](https://www.just-auto.com/news/us-chrysler-rebuilds-long-serving-test-track) |
| 9 | **Ford Michigan PG (Romeo)** | PG | Macomb Co. (Romeo) | **5-mi, 5-lane** concrete high-speed oval. "60° banking" `[unverified, almost certainly wrong]`, banking top 11 ft above grade. Dedicated 1957 | Hills with steep grades | — | Concrete | — | Ford private, 3,880 acres, >100 mi of roads | **Yes:** `highway=raceway` way 508396678 "Proving Ground" | Macomb `[unverified]` | None found | [WP](https://en.wikipedia.org/wiki/Ford_Proving_Grounds), [Dean's Garage](https://www.deansgarage.com/fords-romeo-proving-grounds/), [VDI](https://www.vehicledynamicsinternational.com/features/site-visit-ford-proving-ground.html), [OSM](https://www.openstreetmap.org/way/508396678) |
| 10 | **Ford Dearborn Development Center** | PG | Dearborn, former Ford Airport | **2.5-mi steering & handling course**, 4,000-ft straight, 43-acre VDA, 12-acre wet pad, high-banked curves. $43 M redevelopment 2006 | — | — | — | — | Ford private. 245 vs 365 acres `[conflict]` | `[unverified]` | Wayne `[unverified]` | None found | [Reliable Plant](https://reliableplant.com/Articles/Print/1802?id=1802), [AI-Online](https://www.ai-online.com/2006/06/ford-test-track-transformation-part-of-efforts-to-speed-new-products-to-market-by-a-full-year), [CLUI](https://clui.org/ludb/site/ford-dearborn-development-center) |
| 11 | **FT Techno of America** | PG (rentable) | Fowlerville, Livingston Co. | **3-mi oval**, 4,500-ft straight, 20-acre VDA, low/mid-µ tiles. **1.3-mi handling course planned 2021** `[completion unverified]`. AV track (US$5 M) | — | — | — | — | Private, rented to the industry | `[unverified]` | NRCS 2017–18 (before the 2021+ expansion) | None found | [FTT-A](https://ftt-a.com/), [WHMI 2021](https://whmi.com/news/article/39058), [MarkLines](https://www.marklines.com/en/news/211089) |
| 12 | **American Center for Mobility** | AV | Ypsilanti Twp, former Willow Run | **2.5-mi highway loop**, curved tunnel, overpasses, roundabouts. 500 acres | — | — | — | — | Non-profit, federally designated AV PG | `[unverified]` | Washtenaw `[unverified]` | None found | [WP](https://www.wikipedia.com/wiki/American_Center_for_Mobility), [WardsAuto](https://www.wardsauto.com/technology/autonomous-vehicles-former-b-24-bomber-site-s-future) |
| 13 | **Mcity** | AV | U-M North Campus Research Complex, Ann Arbor | 32-acre mock urban grid (18 acres in early reports `[conflict]`) | — | — | — | — | University | `[unverified]` | Washtenaw | None found | [Deadline Detroit](https://origin.deadlinedetroit.com/articles/ann_arbor_area_is_a_hotbed_for_testing_driverless_cars) |
| 14 | Toyota TTC York Twp | PG (safety) | York Twp, Washtenaw Co. | Opened Oct 2008. **Collision-safety campus, not a circuit.** An ADAS test track is leased; its location `[unverified]` | — | — | — | — | Toyota private | — | — | — | [Toyota 2008](https://media.toyota.ca/en/releases/2008/toyotas-north-american-rd-base-opens-2nd-campus.html), [inkl](https://inkl.com/news/toyota-touts-michigan-s-contribution-to-research-and-development) |
| 15 | Hyundai-Kia ATC | — | Superior Twp | 140-acre site, test track "explored" in 2011, never confirmed built. Hyundai tested at Chelsea | — | — | — | — | — | — | — | — | [AnnArbor.com](https://www.annarbor.com/business-review/hyundai-exploring-expansion-of-ann-arbor-area-operation-including-test-track) |
| 16 | Bosch Flat Rock PG | PG | Flat Rock | Test tracks on 325 acres | — | — | — | — | Bosch private | — | — | — | [Bosch](https://www.bosch-mobility.com/en/solutions/development-services/proving-grounds/) |
| 17 | Michigan Technical Resource Park | PG (off-road) | `[unverified location]` | 3.5-mi off-road tracks | — | — | Off-road | — | Private | — | — | — | [MITRP](https://www.mitrp.com/off-road-vehicle-testing.html) |
| 18 | Smithers Winter PG | PG (winter) | Upper Peninsula `[exact site unverified]` | Ice/snow surfaces | — | — | Ice | — | Private | — | — | — | [DBusiness](https://www.dbusiness.com/from-the-magazine/proving-grounds/) |
| 19 | Kettering GM Mobility Research Center | AV | Flint | AV test track | — | — | — | — | University | — | — | — | [TechCrunch](https://techcrunch.com/?p=1400007) |
| 20 | **Detroit street circuits** | STREET | Detroit | **RenCen 1982–88: 2.493 mi / 17 T** (F1). CART 1989–91: 2.52 mi. **Belle Isle 1992–2022: 2.36 mi / 14 T**. **Downtown 2023–: 1.645–1.7 mi / 9 T** | Flat | — | Street | — | Temporary | Public roads in OSM | Wayne | **Yes:** Detroit 1988 (Rainmaker_87), Belle Isle 2021 v2.3 (2025), acu_detroit | [WP IndyCar](https://en.wikipedia.org/wiki/Detroit_Grand_Prix_(IndyCar)), [Overtake 1988](https://www.overtake.gg/downloads/detroit-1988.68964/), [Overtake BI 2021](https://www.overtake.gg/downloads/detroit-belle-isle-2021.77161/) |
| 21 | Grand Rapids street race | STREET/HIST | Grand Rapids | 1998–99 SCCA street event, details `[not found]` | — | — | — | — | — | — | — | — | [GR Chamber](https://grandrapids.org/news/the-history-of-motorsports-in-west-michigan/) |
| 22 | **Packard Proving Grounds** | HIST (PG) | Shelby Twp, Macomb Co. | **2.5-mi concrete oval, 31° banking** (one source). Opened June 1928 (Duray, 148.7 or 148.17 mph `[conflict]`). **Mostly demolished about 2004.** 158 ft of the oval survives | — | — | Concrete | — | Packard Motor Car Foundation (14-acre remnant), NRHP 2007 | — | — | — | [WP](https://en.wikipedia.org/wiki/Packard_Proving_Grounds), [HMdb](https://www.hmdb.org/m.asp?m=137619), [Shelby Twp](https://www.shelbytwp.org/our-township/resident-information/shelby-township-history/shelby-township-s-historic-packard-proving-grounds) |
| 23 | Oscoda-Wurtsmith Airport | Autocross only | Oscoda (6346 F41) | **No road-course history found.** SCCA Solo/ProSolo venue 2020–22 | Flat | — | Runway concrete | Cones | Airport | Runways in OSM | Iosco | — | [SCCA ProSolo](https://www.scca.com/events/1998189-2021-tire-rack-scca-oscoda-prosolo-oscoda-wurtsmith-airport), [ParkingLotRacing](https://parkinglotracing.org/autocross-location/oscoda-wurtsmith-airport/) |
| 24 | Michigan State Fairgrounds Speedway | OVAL/HIST | Detroit | 1-mi dirt oval, 1951–52 | — | — | — | — | — | — | — | — | [WP list](https://en.wikipedia.org/wiki/List_of_auto_racing_tracks_in_the_United_States) |
| — | Flat Rock Speedway, Owosso Speedway, Berlin, Kalamazoo, etc. | OVAL | — | Excluded by brief. **Not researched in this pass** | | | | | | | | | — |
| — | Lake Orion historic course | ? | — | **`[not found]`.** No evidence of a road course | | | | | | | | | — |
| — | Meadow Brook | — | Rochester Hills | A concours venue, not a circuit. **Not researched in this pass** | | | | | | | | | — |

**Karting (noted separately, not build candidates):** the Michigan Karting Club (founded 1969) has
run karts on MIS, Grattan, GingerMan and Waterford Hills
([KartPulse](https://kartpulse.com/article/print/111)). I-75 Raceway in Birch Run has a "CIK-style
road course" `[unverified: thin directory source]`
([source](https://kartingnearme.pages.dev/guides/karting-in-birch-run-mi.html)).

## B2. "Why drive it": character notes

| Venue | Character | Reference video / map |
|---|---|---|
| **GM Milford Road Course** | GM's private Nürburgring surrogate. **41 m of relief in 4.7 km** on glacial "Bluffs" terrain, a Carousel copy, crest corners that unload the chassis at the apex, tight kerb-lined corners for suspension evaluation, and a >150 mph straight. It averages about 92 mph in a Z/28. Every Corvette, Camaro and Cadillac V since 2004 was tuned here, and no sim has it | Mero lap: https://www.youtube.com/watch?v=tNRWvk5nMu0. Autoweek lap: link in A2.3 |
| **Grattan** | The "driver's track". Off-camber, blind, downhill corners (T3 is "blind downhill off camber"), a mid-corner drop at the T2 apex, a Monza-style bowl, a 160° hairpin, a hidden-apex hairpin and a 3,200-ft straight, about 31 m of relief, on a 1960 family-built former Christmas-tree farm. Its future is uncertain because it's for sale | Turn guide: [Trackpedia](http://trackpedia.racetrackdriving.com/wiki/Turn_by_turn_guide_to_the_Grattan_Raceway_track), [GRM thread](https://grassrootsmotorsports.com/forum/grm/learn-me-grattan-raceway/140483/page1/), [Audipages lap](https://www.audipages.com/on_track/grattan0.html). Onboards indexed at [LapMeta](https://lapmeta.com/en/track/variation/136) |
| **Waterford Hills** | The oldest track in Michigan (1958). Short, narrow, blind crests, 17 m of relief, spectator-hill views, sub-minute laps (record 59.686 s, Provitz 2013) | [racingcircuits](https://racingcircuits.info/north-america/usa/waterford-hills.html) |
| **GingerMan** | Flat, wide (36 ft), safe, with lots of runoff. Technical and rhythm-based, and the extended T10 adds a downhill braking zone. A great teaching track, but the least visually distinct | [Paradigm Shift guide](https://www.paradigmshiftracing.com/gingerman-raceway-track-guide-map.html) |
| **MIS road course** | A 1968 Stirling Moss design that dives from the 18°-banked oval into a flat infield, and was IMSA GTP territory until 1984. A distinct banked-to-flat transition, and nothing else in the fleet has it | [Xtreme 2015 notes](https://www.thextremexperience.com/?p=10463) |
| **Motorsports Gateway Howell** | Brand-new: 144 ft of relief in 1.7 mi, designed by Driven International. Potentially the hilliest per mile in the state, but members-only and very new | [DBusiness](https://www.dbusiness.com/daily-news/motorsports-gateway-in-howell-opens-1-7-mile-13-turn-track-circuit/) |
| **M1 Concourse** | A flat, 9-turn, 1.5-mi track inside a car-condo district. Already laser-scanned for AC | — |

---

# Part C: Ranked recommendation

Scoring is 1–5 per axis, and the product decides the order.
**Data** = imagery + lidar valid for the as-built surface + map/OSM. **Distinct** = a drive nothing
in the fleet or the AC catalogue gives. **Gap** = absence of a good existing AC mod (5 = none).

| Rank | Venue | Data | Distinct | Gap | Product | Verdict |
|---|---|---|---|---|---|---|
| **1** | **GM Milford Road Course** | 3 (lidar 5, NAIP 4, no map and no OSM, so the layout must be found in imagery) | 5 | 5 | **75** | **Build first.** It is the topic's centrepiece, has zero existing mods, and its lidar post-dates the track. Risk: layout identification and the corner count. |
| **2** | **Grattan Raceway** | 4.5 (public, many maps and onboards, 2017–18 lidar, OSM likely) | 4 | 3 (two Patreon mods of unknown quality) | **54** | **Build second**, or **first if the MRC can't be located unambiguously in imagery.** It is also the fleet's best public calibration target: real onboards with lap times to judge against. |
| **3** | **MIS road course (infield + historical exterior)** | 4 | 3 | 4 (oval mod only) | **48** | Third. It exercises *researched* banking (L10: 18° published) on the oval segments with a flat infield, which is a clean test of track-grading on a road course. Layouts infield / exterior / combined share one kn5. |
| 4 | Motorsports Gateway Howell | 2 (**lidar predates the 2023 earthworks**) | 4 | 5 | 40 | **Watch list.** Revisit when post-construction lidar or recent imagery exists. Building now would put a 144 ft track on pre-grading ground. |
| 5 | Waterford Hills | 5 | 3 | 2 | 30 | A quick calibration build. It beats the existing mod only on the post-repave surface. |
| 6 | GingerMan | 5 | 2 | 2 | 20 | A good mod already exists. Skip. |
| 7 | M1 Concourse | 5 | 2 | 1 | 10 | Laser-scanned mod exists. Skip. |
| — | Chelsea / Romeo / Dearborn / FT Techno / ACM | 1–2 | 2 | 5 | ≤20 | Ovals, pads and AV grids with no published road-course layout. Not a drive. |

---

# Part D: LOCATION-DOSSIER, Milford Road Course (`milford_road_course`)

> Filled from research only. **Kevin reviews and approves before any geometry is built.** "Unknown,
> will verify via X" entries are deliberate.

## 1. Identity & intent
- **Kind:** `circuit_port` (a real facility, extant). **Archetype:** `race_circuit`. These agree
  under STANDARDS S6, because `race_circuit` is the implemented preset for a purpose-built facility.
  ⚠ Do **not** write `"archetype": "circuit_port"`, as `projects/nordschleife` and `projects/bathurst`
  do. It is not a key in `scripts/config.py ARCHETYPES`, so it silently matches nothing.
- **Kerb/runoff caveat:** `race_circuit` turns on racing kerbs and engineered runoff. The MRC
  *does* have kerbs ("very tight curb filled corners",
  [LSX](https://www.lsxmag.com/news/video-gms-milford-proving-grounds/)). **Runoff extent is
  unknown.** A proving ground may have guardrail close to the edge, so verify it from video before
  accepting the preset's runoff.
- **Why:** this is GM's private Nürburgring surrogate, 2.9 mi with 41 m of relief, where every modern
  Corvette, Camaro and V-series was sorted. No public sim has it. The drive we're chasing is crests
  that unload the car at the apex, a Carousel copy, and a >150 mph straight, all in a Michigan
  hardwood setting with no grandstands, only test-site austerity.
- **Layouts:** start with **one**, the full course as traced. The SAE design paper calls it a
  "**configurable closed course**" with 20 turns
  ([TRID](https://trid.trb.org/View/1803993)). If imagery shows real cut-through connectors, each
  configuration becomes an extra `layouts[]` entry over **the same kn5** (L8). The corner count
  (17 / 18 / 20) is **set by the trace, not by this file**. No surface fork, so one track.

## 2. Route geometry: facts, per segment
| Segment | Roads | Length | Lanes / width | Kerb / sidewalk | Surface & condition | Notes |
|---|---|---|---|---|---|---|
| Whole course | MRC (private) | **2.9 mi / 4.7 km** ([GM](https://news.gm.com/home.detail.html/Pages/news/us/en/2024/sep/0925-mpg100-20-facts.html), [carsales](https://www.carsales.com.au/editorial/details/chevrolet-corvette-zr1-14336/)). The traced length must land within ±3 % (4.55–4.85 km), or the identification is wrong | **Unknown, will measure** from NAIP at 4+ stations per segment (L1: don't trust defaults). Set `default_width_m` from the median and `width_overrides` per segment | Racing kerbs at tight corners (source above). Kerb profile unknown, will verify from Mero / Autoweek onboard frames | Asphalt `[unverified]`. Condition unknown. GM resurfacing history `[not found]` | Long straight >150 mph ([GM](https://news.gm.com/home.detail.html/Pages/news/us/en/2024/sep/0925-mpg100-20-facts.html)) |
| Per-corner rows | — | — | — | — | — | **To be filled from the trace.** Number the corners in driving order from the start/finish once direction is confirmed from video |

Direction of travel is **unknown, will verify** from the onboard videos (sun position, crest order).
Bridges and culverts: **unknown.** Check whether the MRC crosses another MPG road on a structure.
If it does, it must be declared as a bridge (bare-earth lidar deletes decks, per the `elevation`
skill).

## 3. Elevation & drainage
- **Total relief: 135 ft / 41 m** (SAE 2005 via [TRID](https://trid.trb.org/View/1803993), and
  "plunges 41 metres from hilltop to trough", [carsales](https://www.carsales.com.au/editorial/details/chevrolet-corvette-zr1-14336/)).
  The 3DEP profile must reproduce this within about ±2 m, or the georeference is wrong.
- **DEM:** USGS 3DEP **1 m** from the QL2 projects: OC 2017 / MI_31Co_Oakland_2016 for the Oakland
  side, NRCS 30-County 2017–18 for the Livingston side (A2.4). Both are newer than the 2003–04 build,
  so they are valid. Ledger 0030's "SRTM won" applies **outside the US** (Nordschleife). Here 3DEP
  QL2 is the right source, because SRTM 30 m cannot hold a 41 m crest structure in 4.7 km.
- **Banking:** none is published for the MRC. L10 says a road course gets none *invented*. But the
  **Carousel** replica is by definition a banked bowl, and lidar records real cross-slope: a 10 %
  bank across about 12 m is about 1.2 m, far above QL2's 19.6 cm vertical accuracy. **Take banking
  from lidar cross-sections, never from curvature**, and only where the sections show it.
  `track-grading`'s curvature-derived banking stays **off** for this track.
- **Gotcha:** the elevation stage samples the centerline and smooths. Real cross-slope may be lost.
  If the engine can't carry lateral lidar slope, author the Carousel cross-section in Blender as an
  `AUTH_` object built from the lidar sections (REALISM §4).
- Drainage: unknown, will verify from imagery. Expect kettle wetlands typical of the area
  `[unverified]`.

## 4. Corner-by-corner character
**Unknown in detail: no published corner list exists.** What is sourced:

| Feature | What defines it | Source | Drive-test check |
|---|---|---|---|
| Carousel copy | Nürburgring Carousel simulation, so expect a banked, tight, long-duration left. Concrete-bowl character `[unverified]` | [LSX/RK via search](https://www.rkmotors.com/blog/Milford-Turns-97) | Banked surface continuous with no step at the bowl lip |
| Crest-apex corner | "Aim for the left edge of the approaching rise… chassis unloads over the crest just as it hits the apex" | [Cadillac review, attribution unverified](https://ls1tech.com/forums/automotive-news-media-press/1676199-edmunds-full-test-2014-cadillac-cts-vsport-twin-turbo.html) | Crest radius from lidar, not smoothed away |
| Long straight | >150 mph | [GM](https://news.gm.com/home.detail.html/Pages/news/us/en/2024/sep/0925-mpg100-20-facts.html) | No bumps/km spikes at speed |
| Tight kerbed corners | Suspension-evaluation corners | [LSX](https://www.lsxmag.com/news/video-gms-milford-proving-grounds/) | L9 kerbs flush |
| "Corners modelled on famous tracks" | Which ones besides the Carousel: **unknown, will verify** by matching onboard frames | [LSX](https://www.lsxmag.com/news/video-gms-milford-proving-grounds/) | — |

Method: build the corner table from the trace, then align video frames from the Autoweek Stingray
lap, the Mero ZR1 lap and the Capital City club in-car to trace stations using crest order and the
straight. Record the defining object (guardrail run, tree line, building) per corner.

## 5. Built environment & landmarks
Proving-ground austerity: test garages, low industrial buildings, chain-link and security fencing,
guardrail (MPG is where highway guardrail was developed,
[WMMQ](https://wmmq.com/ixp/690/p/gm-proving-grounds-highway-guardrails/)), and corner and
station markers. **No grandstands, no spectator furniture, no sponsor signage.** No GM logos in the
build (A2.5). Building and barrier inventory per stretch is **unknown, will verify** from onboard
video and NAIP. The circle track's banked concrete and Black Lake may be visible as backdrop, as
static scenery only, depending on where the MRC sits.

## 6. Vegetation & terrain palette
Southeast-Michigan mixed hardwood (oak/hickory/maple), open mown grass verges, some wetland
`[unverified: general regional knowledge, confirm from leaf-on NAIP]`. Ground cover is mown turf
near the track. **The owned library has poplar and pine only** (ASSET-LIBRARY), and pine is wrong
as the dominant species here. Deciduous hardwood is a GAP.

## 7. Atmosphere & light
Latitude about 42.58° N, timezone `America/Detroit`. Great Lakes skies: frequent overcast,
summer haze, autumn colour. Presets worth shipping: `morning`, `noon`, `golden_hour`, plus an
**overcast** preset `[CSP weather]`. The mood photo is unknown, will pick from the Autoweek lap
frames. `true_north_rotation_deg` is derived by `lighting` and written back (L2).

## 8. Asset plan: owned first
| Need | Owned asset | Conversion notes | Placement | Or GAP |
|---|---|---|---|---|
| Guardrail / armco | `Barrier set` (`Barrier02.obj`, `Road_Barrier.blend`) | m / Y-up check, PoT textures | Per video-verified runs | Likely GAP: a true W-beam guardrail model |
| Chain-link / security fence | procedural `make_chainlink` | — | Perimeter and paddock | — |
| Deciduous hardwoods | — | — | Tree lines | **GAP**: oak/maple set |
| Grass / verge | `textures-2/grass_path_2` 4K | EXR→PNG n/a, confirm CC0 | Verges | — |
| Concrete (Carousel bowl, pads) | `textures-2/concrete_wall_008` 4K | PoT | Carousel surface | — |
| Test garages | `ModularBuildings.blend1` (re-save first), `building_1.blend` | 1.23 GB backup file | Paddock | — |
| Sky | `bloem_hill_02_4k.exr` | EXR→PNG for AC | — | — |

## 9. Data sources & capture assets
| Item | Where | Status |
|---|---|---|
| NAIP orthoimagery covering MPG (latest MI vintage, plus one older for leaf-off contrast if available) | USDA/USGS EarthExplorer or the NAIP COG on AWS (`naip-analytic`) | **To pull** |
| Annotated Google Maps view of MPG | [Gadgetopia](https://archive.gadgetopia.com/post/6095/) | Use to *select* the MRC (L1: selection aid only) |
| 3DEP 1 m DEM tiles, Oakland + Livingston | [USGS Lidar Explorer](https://apps.nationalmap.gov/lidar-explorer/) / TNM, projects listed in A2.4 | **To pull** |
| Lidar point cloud for cross-sections (Carousel banking) | Same projects, LAZ | **To pull** for the bank sections only |
| Onboard laps | A2.3 table | Frame-grab for §4 |
| Lap-time anchor | Z/28 1:53.71 ([LSX](https://www.lsxmag.com/news/video-camaro-z28-vs-boss-302-at-the-milford-proving-grounds)) | For QA |
| OSM | Overpass query in the handoff | **To run**. If ways exist, prefer `gps-extraction` |

## 10. Location-specific QA
1. **Traced length is 4.55–4.85 km.** If not, the wrong loop was traced.
2. **Profile relief is 41 ± 2 m** (DEM min to max along the centerline).
3. **The Carousel replica's bank comes from lidar sections**, has no step at the lip, and drive_test
   reports no tyre crossing a slope kink.
4. **The crest-apex corner unloads but does not launch**: a vertical-curvature check at the crest
   station, and a Kevin seat-time note.
5. **Lap time is in family:** a Z/28-class car (an AC stand-in such as a Camaro/Mustang GT4-ish,
   `[pick at test]`) laps within about ±5 % of 1:53.71. That is a sanity range, not a gate.
6. **Top speed on the straight passes 150 mph** in a ZR1-class car without bottoming.
7. **It reads as a proving ground, not a club circuit**: no grandstands, guardrail edges, hardwood
   tree lines. That is the §Look row.
8. Standard gates: drive_test → audit_mesh → verify_kn5 → kn5_ground_check on the **built**
   artifact (L5).

## 11. Build plan

> **Rewritten 2026-10-28 (Kevin: "build these the same way that we build Lake Murray 0.19.1").** The first
> version of this section prescribed the engine-era pipeline (`aerial-tracing` → `elevation` → mesh → gates →
> kn5), and v0.1.0 was built that way and retired the same evening. The track builds through the ship chain:
> `tools/ship_track.sh milford-road-course`, steps in [`ship.json`](ship.json).

1. **Draft (the engine, as a draft only).** `gps` on `source.type from_track` (the NAIP-traced fixes with
   their measured widths, `source/mrc_fixes.json`) → `elev` (3DEP 1 m, both counties) → `project` → `mesh`
   (`data/track.obj`: ribbon, kerbs, verge, the guard walls the drops ask for, ground) → **`underlay`**
   (`scripts/blender/underlay.py`: the OBJ into `loop.blend` as `GEN_road` / `GEN_kerb` / `GEN_wall` /
   `GEN_terrain` / `GEN_misc`, plus `GEN_refs`: the centreline and a station marker every 500 m).
2. **Author in Blender (`AUTH_*`, never regenerated).** First pass: nothing — the draft ships so the seat
   can judge it. Then, in order of what the seat says: the real corner banking from the lidar sections
   (4–8 %, Part D §3; the draft builds the corners flat, and it is never curvature-invented, L10); the
   carousel; the stone walls as guardrail where the real course has rail; signs only from `signs.json`.
3. **Prep → split → export** from airoso's `scripts/ac` (never engine-july: San Diego's alone). One
   layout, `full`, clockwise; the AI line is the writer's draft until recorded in game.
4. **Gates on the built kn5:** `drive_test` → `audit_mesh` → `kn5_ground_check`. Thresholds unchanged
   (GATES-CHANGELOG).
5. **Install** as `content/tracks/milford_road_course`, "doooom Michigan - Milford Road Course" (Kevin, 2026-10-28:
   "K10 is gone. doooom.").
6. **First question for the drive test** stands: "Does the 41 m of relief feel like a hill course, or did
   smoothing flatten the crests?" — and now also: "Does the 27 % climb to the start/finish read as the
   lidar says, or as a wall?"

**Kevin's approval:** ☑ approved as-is ("Build Milford first") · ☐ approved with changes — date: 2026-10-28.
What the build found against this file is in `source/route-notes.md`: OSM has the course but draws
it wrong, the relief matches (39.7 m) and the length doesn't (4.07 km, not 4.7).

---

# Part E: Opus handoff, concrete first steps

**Tier note (CLAUDE.md agent tiers):** geometry authoring and the build-gate loop go on the top model at
`effort: high`. Re-running gates, md5/manifest checks and tile listing go on `sonnet` low/medium.

1. **Confirm network.** This research session could not reach Overpass, Nominatim, TNM or OSM.
   Check the build session can, and if not, have Kevin allow those hosts.
2. **OSM check, first, because it decides the front-end** (MPG bbox, approximate: the boundary
   roads are Commerce Rd N, Pleasant Valley Rd W, Hickory Ridge Rd E. Get the exact bbox from
   Nominatim on "Milford Proving Ground").
   ```
   [out:json][timeout:60];
   area["name"="Milford Charter Township"]->.a;   // plus Brighton Twp, or use a bbox
   ( way["highway"="raceway"](area.a);
     way["landuse"="industrial"]["operator"~"General Motors"](area.a);
     way["highway"]["access"~"private|no"](area.a); );
   out geom;
   ```
   If raceway ways exist, use `gps-extraction` against them, then verify widths and alignment against
   NAIP. Otherwise use **`aerial-tracing`**.
3. **Imagery:** pull the latest **NAIP** GeoTIFF/COG for the MPG tiles. Reproject and clip to
   **EPSG:4326, north-up** so the two corner control points are exact raster corners, which is what
   `georef.py`'s two-point north-up affine assumes. Over 4–5 km a Web-Mercator screenshot is
   acceptable but worse. Export PNG for the auto-trace attempt. Expect to need a **manual
   `trace_px`**, because the infield and test roads cross and will confuse the skeleton.
4. **Locate the MRC** using the [Gadgetopia annotated map](https://archive.gadgetopia.com/post/6095/)
   as a selection aid (L1), then **prove the identification** by the trace length (4.7 km ± 3 %) and
   the DEM relief (41 m). If both don't match, stop and report. Don't force it.
5. **DEM:** USGS 3DEP 1 m tiles covering the MRC bbox, from MI_31Co_Oakland_2016 / OC 2017 and NRCS
   30-County (Livingston). The **county line runs through the site**, so expect two projects and
   check the vertical datum and geoid match at the seam (both should be NAVD88; verify).
6. **Config sketch** (airoso track dir; values in `<>` come from steps 3–5, never from here):
   ```json
   { "name": "Milford Road Course (unofficial)", "slug": "milford_road_course",
     "loop": true, "archetype": "race_circuit", "road_surface": "tarmac",
     "location": {"lat": "<centroid of trace>", "lon": "<…>", "timezone": "America/Detroit"},
     "source": {"type": "aerial", "screenshot": "source/naip_mrc.png",
       "control_points": ["<NW raster corner lonlat>", "<SE raster corner lonlat>"],
       "_note": "NAIP <vintage>, EPSG:4326 north-up clip; MRC identified via length 4.7 km + relief 41 m; layout unpublished by GM"},
     "default_width_m": "<median measured>", "width_overrides": ["<per segment>"],
     "layouts": [{"id": "full"}] }
   ```
7. **Expected gotchas**
   - **Turn-count trap:** GM says 17, the SAE paper says 20 (configurable), a forum says 18. Trace
     what's there. Connectors become layouts (L8) only if they are visibly paved links.
   - **Bare-earth bridge deletion** if the MRC passes over or under another MPG road. Declare it in
     `capture.bridges`.
   - **Smoothing flattens crests.** Watch the crest radii and the 41 m relief after smoothing.
   - **Carousel bank:** lidar cross-sections only. No curvature-invented banking (L10).
   - **Archetype string:** `race_circuit`, not `circuit_port` (S6 silent-mismatch).
   - **Branding:** no GM marks in textures, UI, or `ui_track.json`. Don't describe it as official.
   - **The Wikipedia 3.5-mi circle / 1.4-mi straight list is Yuma, not Milford** (A1 note).
8. **Fallback / #2:** if step 4 fails, pivot to **Grattan** (`circuit_port`/`race_circuit`, 43.09667,
   −85.38333). Run the OSM check first, because a public club track is likely mapped. Lidar is expected from the Kent
   County NRCS 30-county flight `[unverified dates]`. Turn numbering varies by map vintage (10 vs 12–13), so number from
   the trace. QA anchor: published onboard laps on LapMeta, e.g. a Camaro ZL1 at 1:19.460 on the
   1.81-mi CW variant.
9. **#3 (MIS road course):** the oval banking is published (18° in the turns; straights
   `[conflict]`: 12°/5° per WP vs 5°/2° per recent Jayski). **Measure the straights from lidar** to
   settle it. Infield, exterior and combined are three layouts over one kn5.
