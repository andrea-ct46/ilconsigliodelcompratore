/**
 * Script Google Apps Script per riempire un foglio Google con dati da Amazon PA-API 5.0.
 * Colonna A: ASIN di input.
 * Colonne B-E: Titolo, Descrizione, Immagine, Link affiliato.
 */

const ACCESS_KEY = "YOUR_ACCESS_KEY";   // Placeholder
const SECRET_KEY = "YOUR_SECRET_KEY";   // Placeholder
const ASSOCIATE_TAG = "YOUR_ASSOCIATE_TAG"; // Placeholder

const HOST = "webservices.amazon.it";
const REGION = "eu-west-1";
const SERVICE = "ProductAdvertisingAPI";

function aggiornaProdottiDaAmazon() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    Logger.log("Nessun ASIN trovato");
    return;
  }

  const asinValues = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
  const asins = asinValues.map(([asin]) => (asin || "").toString().trim()).filter(Boolean);
  if (!asins.length) return;

  const resultsMap = {};

  for (let i = 0; i < asins.length; i += 10) {
    const batch = asins.slice(i, i + 10);
    try {
      const batchResult = callPaApi(batch);
      Object.assign(resultsMap, batchResult);
    } catch (err) {
      Logger.log("Errore batch " + batch.join(",") + ": " + err);
    }
  }

  const output = asinValues.map(([asinRaw]) => {
    const asin = (asinRaw || "").toString().trim();
    const item = resultsMap[asin];
    if (!asin || !item) {
      return ["", "", "", ""];
    }
    return [item.title || "", item.description || "", item.image || "", item.link || ""];
  });

  if (output.length) {
    sheet.getRange(2, 2, output.length, 4).setValues(output);
  }
}

function callPaApi(asinBatch) {
  const now = new Date();
  const amzDate = Utilities.formatDate(now, "GMT", "yyyyMMdd'T'HHmmss'Z'");
  const dateStamp = Utilities.formatDate(now, "GMT", "yyyyMMdd");

  const body = JSON.stringify({
    ItemIds: asinBatch,
    Resources: [
      "Images.Primary.Large",
      "ItemInfo.Title",
      "ItemInfo.Features",
      "ItemInfo.ContentInfo",
      "ItemInfo.ByLineInfo",
      "EditorialReviews",
    ],
    PartnerTag: ASSOCIATE_TAG,
    PartnerType: "Associates",
    Marketplace: "www.amazon.it",
  });

  const canonicalURI = "/paapi5/getitems";
  const canonicalHeaders =
    "content-type:application/json; charset=utf-8\n" +
    "host:" + HOST + "\n" +
    "x-amz-date:" + amzDate + "\n";
  const signedHeaders = "content-type;host;x-amz-date";

  const payloadHash = toHex(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, body));
  const canonicalRequest = [
    "POST",
    canonicalURI,
    "",
    canonicalHeaders,
    signedHeaders,
    payloadHash,
  ].join("\n");

  const algorithm = "AWS4-HMAC-SHA256";
  const credentialScope = [dateStamp, REGION, SERVICE, "aws4_request"].join("/");
  const stringToSign = [
    algorithm,
    amzDate,
    credentialScope,
    toHex(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, canonicalRequest)),
  ].join("\n");

  const signingKey = getSignatureKey(SECRET_KEY, dateStamp, REGION, SERVICE);
  const signature = toHex(Utilities.computeHmacSha256Signature(stringToSign, signingKey));

  const authorizationHeader =
    algorithm +
    " Credential=" + ACCESS_KEY + "/" + credentialScope +
    ", SignedHeaders=" + signedHeaders +
    ", Signature=" + signature;

  const response = UrlFetchApp.fetch("https://" + HOST + canonicalURI, {
    method: "post",
    contentType: "application/json; charset=utf-8",
    payload: body,
    headers: {
      "Content-Encoding": "amz-1.0",
      "X-Amz-Date": amzDate,
      Authorization: authorizationHeader,
    },
    muteHttpExceptions: true,
  });

  if (response.getResponseCode() >= 300) {
    throw new Error("PA-API risposta " + response.getResponseCode() + ": " + response.getContentText());
  }

  const data = JSON.parse(response.getContentText());
  const map = {};

  if (data.ItemsResult && data.ItemsResult.Items) {
    data.ItemsResult.Items.forEach((item) => {
      const asin = item.ASIN;
      const title = item.ItemInfo?.Title?.DisplayValue || "";
      const image = item.Images?.Primary?.Large?.URL || "";
      const detail = item.DetailPageURL || "";
      const description = getDescription(item);
      map[asin] = { title, description, image, link: detail };
    });
  }

  if (data.Errors) {
    data.Errors.forEach((err) => Logger.log(err.Code + ": " + err.Message));
  }

  return map;
}

function getDescription(item) {
  const editorial = item.EditorialReviews?.DisplayValues;
  if (editorial && editorial.length) {
    return editorial[0];
  }
  const features = item.ItemInfo?.Features?.DisplayValues;
  if (features && features.length) {
    return features.join(" • ");
  }
  return "";
}

function getSignatureKey(key, dateStamp, regionName, serviceName) {
  const kDate = Utilities.computeHmacSha256Signature(dateStamp, "AWS4" + key);
  const kRegion = Utilities.computeHmacSha256Signature(regionName, kDate);
  const kService = Utilities.computeHmacSha256Signature(serviceName, kRegion);
  return Utilities.computeHmacSha256Signature("aws4_request", kService);
}

function toHex(bytes) {
  return bytes
    .map(function (x) {
      const hex = (x < 0 ? x + 256 : x).toString(16);
      return hex.length === 1 ? "0" + hex : hex;
    })
    .join("");
}
