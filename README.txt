AKSA Residence - interactive masterplan

Run:   npm install, then npm run dev (http://localhost:4321) or npm run build (static site in dist/).
       The build reads sales facts from the CRM when CRM_API_URL and CRM_API_KEY are set (.env.local, never
       committed); without them it uses src/data/site.json. npm run sync-crm saves the CRM's facts into site.json.
       SITE_URL (the public address) adds canonical links and sitemap.xml.
Pages: index.html (3D explorer), project.html (all homes), homes/<code>.html (one per home, e.g. homes/b0d.html).

Masterplan   rotating aerial (8 angles) of the two blocks and the commercial building, rendered from a 3D
             model of the architect's drawings; project only, with traffic and people in the loops.
             Hover the buildings or the amenity pins; click to choose a floor.
Residences   close-up of both blocks; click a floor for the architect's plan, click a unit for its fração,
             typology, area and aspect (price on request). 320 homes, 160 per block.
Amenities    pools and decks, pergolas, play areas, gardens, terraces, balconies, car park, boulevard,
             cycle path, commercial building, each with the studio renders.
Gallery      the 28 studio renders.   Location  map, walking times, photos.

Folders: public/media/mp and public/media/close (aerial stills, loops, rotations), media/plans, media/gallery,
media/amenities, media/loc; src/data/site.json; src/pages (pages), src/lib (CRM sync). tools/ holds the pipeline (render3.html scene, jobs.py, build4.py).
Map data (c) OpenStreetMap contributors, ODbL. Location photos: Wikimedia Commons, CC BY-SA.
