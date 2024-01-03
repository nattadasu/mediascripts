/**
 * Table headers.
 * @type {string[]}
 * @example
 * headers[0] // "ID"
 */
const headers = [
  "ID","Poster","📡","Title","Type","Source","Rating","Year","Season","Origin", "Watch In","Status","🔁","Cur","Tot","%","Est","Catched up?","Offset","Start","End","Days","🟣","Weight","Story","Chara","Acting","Visual","Theme","Sound","Bias", "Old","aDB","AL","AP","aS","AN","KZ","KT","LC","MAL","NM","OO","SH","SMK","SY","TR","Last Added","Last Updated","AnimeAPI Data","Jikan Data"
];


/**
 * Converts a date string to epoch time in seconds.
 * @param {string} dateString - The date string to convert.
 * @returns {number} The epoch time in seconds.
 */
function convertToEpochTime_(dateString) {
  const date = new Date(dateString);
  return date.getTime() / 1000; // Convert to seconds
}

/**
 * Fetches a raw file from a URL.
 * @param {string} url - The URL to fetch.
 * @returns {string} The raw data.
 * @customfunction
 */
function IMPORTRAW(url) {
  const options = {
    method: "get",
    headers: {
      "User-Agent": "GoogleSheet/1 (nattadasu's Ultimate Rating System)",
    },
  };

  const response = UrlFetchApp.fetch(url, options);
  const content = response.getContentText();

  if (url.startsWith("https://api.jikan.moe/v4/users")) {
    console.info("Found forced remover");
    const /** @type {ResponseData} */ data = JSON.parse(content);

    const keysToDelete = ['about', 'updates', 'favorites'];

    for (const key of keysToDelete) {
      delete data.data[key];
    }

    // Convert 'data' back to JSON
    const jsonRet = JSON.stringify(data.data);
    console.log(jsonRet);

    // Set Expires and Last-Modified headers
    const headers = response.getAllHeaders();
    data.data["expires"] = convertToEpochTime_(headers.Expires);
    data.data["last_modified"] = convertToEpochTime_(headers["Last-Modified"]);

    return JSON.stringify(data.data);
  }

  return content;
}

/**
 * Parses raw JSON to extract a specified key.
 * @param {string} jsonData - The JSON data.
 * @param {string} key - The key to extract.
 * @returns {any} The extracted data.
 * @customfunction
 */
function PARSEJSON(jsonData, key) {
  const /** @type {Record<string, any>} */ data = JSON.parse(jsonData);
  return data[key];
}

/**
 * Parses nested JSON using a key path.
 * @param {string} jsonData - The JSON data.
 * @param {string} keyPath - The key path to navigate.
 * @returns {any} The extracted data.
 * @customfunction
 */
function PARSENESTEDJSON(jsonData, keyPath) {
  const /** @type {Record<string, any>} */ data = JSON.parse(jsonData);
  const keys = keyPath.split('.');
  let result = data;

  for (const key of keys) {
    if (!result || !result.hasOwnProperty(key)) {
      throw new Error("Failed to parse JSON");
    }
    result = result[key];
  }

  return result;
}

/**
 * Create a slug from a title.
 * @param {string} title - The title to convert to a slug.
 * @return {string} - The generated slug.
 * @customfunction
 */
function CREATESLUG(title) {
  // Convert to lowercase and remove special characters
  let slug = title.toLowerCase() // make lowercase
    .replace(/\s+/g, '-') // replace spaces with -
    .replace(/[^\w-]/g, '') // remove all non-word chars
    .replace(/--+/g, '-') // replace multiple - with single -
    .replace(/^-+|-+$/g, ''); // trim - from end of text

  return slug;
}


/**
 * Find a column by its header.
 * @param {string} column - The column to find.
 * @return {number} - The column number.
 * 
 * @example
 * findColumn_("ID"); // 1
 */
function findColumn_(column) {
  return headers.indexOf(column) + 1;
}


/**
 * Find a column by its header.
 * @param {number} location - The column number.
 * @return {string} - The column letter.
 * 
 * @example
 * columnIntToLetter_("ID"); // A
 */
function columnIntToLetter_(location) {
  let result = '';
  let num = findColumn_(location);
  while (num > 0) {
    const remainder = (num - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    num = Math.floor((num - 1) / 26);
  }
  return result;
}


/**
 * Assigns media IDs to the corresponding service links.
 * @param mediaId - The media ID.
 * @param {string} service - The service to use.
 * @param {string} title - The title of the media. Required for some services.
 * 
 * @returns {string} The service link.
 */
function assignLinks_(mediaId, service, title = "") {
  const serviceLinks = {
    "aDB": `https://anidb.net/anime/${mediaId}`,
    "AL": `https://anilist.co/anime/${mediaId}`,
    "AP": `https://www.anime-planet.com/anime/${mediaId}`,
    "aS": `https://www.anisearch.com/anime/${mediaId}`,
    "AN": `https://annict.com/works/${mediaId}`,
    "KZ": `https://kaize.io/anime/${mediaId}`,
    "KT": `https://kitsu.io/anime/${mediaId}`,
    "LC": `https://livechart.me/anime/${mediaId}`,
    "MAL": `https://myanimelist.net/anime/${mediaId}`,
    "NM": `https://notify.moe/anime/${mediaId}`,
    "OO": `https://otakotaku.com/anime/view/${mediaId}/${CREATESLUG(title)}`,
    "SH": `https://shikimori.me/animes/${mediaId}`,
    "SMK": `https://api.simkl.com/redirect?mal=${mediaId}`,
    "SY": `https://db.silveryasha.web.id/anime/${mediaId}`,
    "TR": `https://trakt.tv/${mediaId}`,
  };

  return serviceLinks[service];
}

/**
 * Check if the string provided is a link
 * 
 * @param {string} URL to test
 * @return {bool} Boolean
 */
function isValidURL_(testUrl) {
  // Regular expression to match a URL pattern
  const urlPattern = /^(https?|ftp):\/\/[^\s/$.?#].[^\s]*$/i;
  return urlPattern.test(testUrl);
}

/**
 * Triggered when a cell in the sheet is edited.
 * @param {GoogleAppsScript.Events.SheetsOnEdit} e - The event object.
 */
function onEdit(e) {
  console.log("onEdit triggered");
  const { source, range } = e;
  const sheet = source.getActiveSheet();
  const row = range.getRow();
  const col = range.getColumn();
  const rangeValue = range.getValue();

  // Set date
  const date = new Date();
  const iso8601 = date.toISOString();

  const colId = findColumn_("ID");
  const colStatus = findColumn_("Status");
  const colEps = findColumn_("Cur");
  const colEnd = findColumn_("End");
  const colWeight = findColumn_("Weight");
  const colTitle = findColumn_("Title");
  const colJsonData = findColumn_("Jikan Data");

  const retainedColums = [
    findColumn_("Poster"),
    colTitle,
    findColumn_("Season"),
    findColumn_("MAL"),
    findColumn_("SH"),
    findColumn_("SMK"),
    findColumn_("%"),
    findColumn_("Est"),
    findColumn_("Catched up?"),
    findColumn_("Days"),
    findColumn_("🟣"),
    colWeight,
  ];

  // Check if the edited cell is in one of the monitored columns
  if (
    (sheet.getName() == "Anime" || sheet.getName() == "Manga") &&
    row > 2
  ) {
    // Replace URL to IDs
    if (col == colId && rangeValue != "" && rangeValue != null) {
      console.info(`ID column updated in row ${row}`);
      let id = "";
      if (typeof rangeValue === 'string' && rangeValue.includes("/")) {
        const url = rangeValue;
        if (url.includes("myanimelist.net")) {
          id = url.split("/")[4];
        } else if (url.includes("shikimori")) {
          id = url.split("-")[0].replace(/\D/g, "");
        } else if (url.includes("myani.li")) {
          id = url.split("/")[5];
        }
        id = parseInt(id);
      } else {
        id = rangeValue;
      }
      console.info(`Setting ID in row ${row} to ${id}`);
      sheet.getRange(row, colId).setValue(id);
      sheet.getRange(row, findColumn_("Last Added")).setValue(iso8601);
      console.info(`Sleeping for 3 seconds to give fetcher time`);
      Utilities.sleep(3000); // Sleep the event to give fetcher time
    }

    // Remove data if MAL ID removed
    if (col == colId && (range.getValue() == "" || range.getValue() == null)) {
      // Clear values in the entire row except for the columns to retain
      const configSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Config");
      const config = configSheet.getRange(6, 2).getValue();
      if (!config) {
        for (let i = 1; i <= sheet.getLastColumn(); i++) {
          if (!retainedColums.includes(i)) {
            console.info(`Clearing row ${row}, column ${i}`);
            sheet.getRange(row, i).clearContent();
          }
        }
      }
      console.info(`Clearing poster in row ${row}`);
      sheet.getRange(row, findColumn_("Poster")).setValue(null);
      console.info(`Clearing note in row ${row}'s title`);
      const modTitle = sheet.getRange(row, colTitle)
      modTitle.setNote(null);
      modTitle.clearContent();
      console.info(`Resetting activity notice in row ${row}`);
      sheet.getRange(row, colTitle)
        .setFormula(`=IF(A${row}<>"", "Loading... Do not modify sheet until data fully loads!", "")`)
      console.info(`Resetting airing status in row ${row}`);
      sheet.getRange(row, findColumn_("📡")).setValue(false);
      console.info(`Resetting Jikan formula in row ${row}`);
      sheet.getRange(row, colJsonData)
        .setFormula(`=IF(A${row}<>"", IMPORTRAW("https://api.jikan.moe/v4/anime/"&$A${row}), "")`);
      console.info(`Resetting AnimeAPI formula in row ${row}`);
      sheet.getRange(row, findColumn_("AnimeAPI Data"))
        .setFormula(`=IF(A${row}<>"", REGEXREPLACE(IMPORTRAW("https://animeapi.my.id/myanimelist/"&$A${row}),"\n",""),"")`);
      sheet.setRowHeight(row, 21);
      console.log(`Finished resetting row ${row}`);
      return 0;
    }

    // Update the "Last Updated" cell with the current timestamp
    console.info(`Setting last updated in row ${row}`);
    sheet.getRange(row, findColumn_("Last Updated")).setValue(iso8601);

    // add identifiable location to watch
    if (col == findColumn_("Watch In")) {
      console.info("Got an event for Watch In value")
      const watchIndex = sheet.getRange(row, findColumn_("Watch In"));
      const watchValue = watchIndex.getValue();

      if (isValidURL_(watchValue)) {
        console.info(`${watchValue} is an URL`)
        const stripUrl = watchValue.split("/")[2];
        const watchFormula = `=HYPERLINK("${watchValue}", IMAGE("https://www.google.com/s2/favicons?domain=${stripUrl}"))`

        watchIndex.setFormula(watchFormula);
      } else if (watchValue === "local") {
        watchIndex.setValue("💾");
        watchIndex.setNote("Anime available locally");
      } else {
        console.error(`${watchValue} is not an URL`);
      }
      return 0;
    }
  
    const status = sheet.getRange(row, colStatus);
    const watch_status = status.getValue();
    const start = sheet.getRange(row, findColumn_("Start"));
    // set date and status to finished if current == total
    if (col == colEps && range.getValue() == sheet.getRange(row, findColumn_("Tot")).getValue()) {
      console.info(`Setting status to Finished in row ${row}`);
      status.setValue("Finished");
      console.info(`Setting end date in row ${row}`);
      const endDate = sheet.getRange(row, colEnd); 
      const validate = [0, "", null];
      if (validate.includes(endDate.getValue())) {
        endDate.setValue(iso8601.split('T')[0]);
      }
      if (validate.includes(start.getValue())) {
        start.setValue(iso8601.split('T')[0]);
      }
      return 0;
    }

    // handle status change
    if (col == colEps && Number(range.getValue()) > 0) {
      if (watch_status === "Finished") {
        console.info(`Setting status to Rewatch in row ${row}`);
        status.setValue("Repeating");
        let note = status.getNote();
        if (note) { note += "\n"; }
        note += `* Rewatch started on ${iso8601.split('T')[0]}`;
        status.setNote(note);
        let replayValue = sheet.getRange(row, findColumn_("🔁"));
        replayValue.setValue(replayValue.getValue() + 1);
        console.info(`Setting end date in row ${row}`);
        sheet.getRange(row, colEnd).setValue(iso8601.split('T')[0]);
        return 0;
      } else if (watch_status === "Planned") {
        console.info(`Setting status to Current in row ${row}`);
        status.setValue("Current");
        if (!start.getValue()) {start.setValue(iso8601.split('T')[0])}
        return 0;
      } else if (watch_status === "Dropped" || watch_status === "Holding") {
        console.info(`Setting status to Watching in row ${row}`);
        status.setValue("Current");
        return 0;
      }
    }

    // Handle the rest of logic
    if (col == colId && sheet.getRange(row, colJsonData).getValue()) {
      console.info(`Parsing JSON data in row ${row}`);
      // If column A (ID) is updated and there's JSON data in column C
      const aniapiDataCol = sheet.getRange(row, findColumn_("AnimeAPI Data"));
      const aniapiData = JSON.parse(aniapiDataCol.getValue());
      const jsonDataCol = sheet.getRange(row, colJsonData);
      const jsonData = JSON.parse(jsonDataCol.getValue());

      jsonDataCol.setValue(JSON.stringify(jsonData));
      aniapiDataCol.setValue(JSON.stringify(aniapiData));

      if (jsonData.data) {
        if (jsonData.data.synopsis) {
          // Extract the synopsis from the JSON data
          const synopsis = jsonData.data.synopsis;

          // Set the note in column D with the synopsis
          console.info(`Setting synopsis in row ${row}`);
          sheet.getRange(row, colTitle).setNote(synopsis);
        }

        const statusData = sheet.getRange(row, colStatus).getValue();

        if (statusData == "" || statusData == null) {
          console.info(`Setting status to Planned in row ${row}`);
          sheet.getRange(row, colStatus).setValue("Planned");
        }

        sheet.getRange(row, findColumn_("🔁")).setValue(0);

        let assignments = [
          ["Type", "type"],
          ["Source", "source"],
          ["Tot", "episodes"],
        ]

        for (const [colName, key] of assignments) {
          if (jsonData.data[key]) {
            console.info(`Setting ${colName} in row ${row} to ${jsonData.data[key]}`);
            sheet.getRange(row, findColumn_(colName)).setValue(jsonData.data[key]);
          }
        }

        try {
          sheet.getRange(row, findColumn_("📡")).setValue(jsonData.data.airing);
        } catch {}

        const modTitle = sheet.getRange(row, colTitle);
        let roTitle = jsonData.data.title.replace(/"/g, '""');
        let enTitle = roTitle;
        let naTitle = roTitle;

        if (jsonData.data.title_english) {
          enTitle = jsonData.data.title_english.replace(/"/g, '""');
        }
        if (jsonData.data.title_japanese) {
          naTitle = jsonData.data.title_japanese.replace(/"/g, '""');
        }
        modTitle.setFormula(`=LET(
  id, $A${row}, jikan, $${columnIntToLetter_("Jikan Data")}${row},
  IF(
    jikan <> "",
    LET(
      mal_url, "https://myanimelist.net/anime/",
      mali, "https://myani.li/#/anime/details/",
      shikimori, "https://" & Config!$B$1 & "/animes/",
      msym, "https://malsync.moe/pwa/#/anime/",
      msys, "https://malsync.moe/pwa/#/anime/shi:",
      config, Config!$B$2,
      fallback, "${roTitle}",
      title, IFS(
        Config!$B$4 = "Transliterated",
        fallback,
        Config!$B$4 = "English",
        "${enTitle}",
        Config!$B$4 = "Native",
        "${naTitle}"
      ),
      HYPERLINK(
        JOIN(
            "",
            IFS(
                config = "MyAnimeList",
                mal_url,
                config = "MyAni.li",
                mali,
                config = "Shikimori",
                shikimori,
                config = "MAL-Sync MAL",
                msym,
                config = "MAL-Sync Shiki",
                msys
            ),
            id
        ),
        IF(
            title <> "",
            title,
            fallback
        )  
      )
    ),
    ""
  )
)`);

        const dateparse = jsonData["data"]["aired"]["from"]; //2023-07-01T00:00:00+00:00
        let parseddate = null;
        if (dateparse) {
          parseddate = new Date(dateparse);
        }
        const colYearIndex = findColumn_("Year");
        const colYear = sheet.getRange(row, colYearIndex);

        try {
          if (parseddate) {
            console.info("Guessing year info!");
            colYear.setValue(parseddate.toISOString().slice(0, 10));
          } else {
            console.info("Can't find any key for year");
            colYear.setValue(null);
          }
        } catch (err) {
          console.error(`Whoops, there's unknown err when proccessing year! Err: ${err}`)
          colYear.setValue(null);
        }

        let ageRating = jsonData.data.rating;
        // if its not null, split it and get the first element
        if (ageRating) {
          ageRating = ageRating.split(" ")[0];
        }
        sheet.getRange(row, findColumn_("Rating")).setValue(ageRating);

        sheet.getRange(row, findColumn_("Poster")).setFormula(`=LET(url, "${jsonData.data.images.jpg.large_image_url}", HYPERLINK(url, IMAGE(url)))`);
        // sheet.setRowHeight(row, 97);
      }

      if (aniapiData) {
        // dynamically populate websiteColumns, from the headers
        // from "aDB" to "TR", skip "MAL", "SH", and "SMK"
        console.info(`Populating website columns in row ${row}`);
        let websiteColumns = [];
        const idxStart = headers.indexOf("aDB");
        const idxEnd = headers.indexOf("TR");
        for (let i = idxStart; i <= idxEnd; i++) {
          if (headers[i] !== "MAL" && headers[i] !== "SH" && headers[i] !== "SMK") {
            // push the index number
            websiteColumns.push(i + 1);
          }
        }

        // Loop through the website columns
        for (const wcol of websiteColumns) {
          let url = "";
          let media_id = "";
          let head = headers[wcol - 1];
          const shortToLong = {
            "aDB": "anidb", "AL": "anilist", "AP": "animeplanet", "aS": "anisearch",
            "AN": "annict", "KZ": "kaize", "KT": "kitsu", "LC": "livechart",
            "NM": "notify", "OO": "otakotaku", "SH": "shikimori", "SMK": "myanimelist",
            "SY": "silveryasha"
          };
          // if the column is "TR", do additional check
          if (wcol === headers.indexOf("TR") + 1 && aniapiData.trakt_season) {
            media_id = `shows/${aniapiData.trakt}/seasons/${aniapiData.trakt_season}`;
          } else if (wcol === headers.indexOf("TR") + 1 && aniapiData.trakt) {
            media_id = `${aniapiData.trakt_type}/${aniapiData.trakt}`;
          } else {
            media_id = aniapiData[shortToLong[head]];
          }
          if (media_id) {
            url = assignLinks_(media_id, head, aniapiData.title);
            console.info(`Setting ${head} in row ${row} to ${url}`);
            sheet.getRange(row, wcol).setValue(url);
          }
        }
      }
    }
  }
}
