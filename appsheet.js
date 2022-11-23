

function yahooBidAsk(ticker) {
  //const ticker="SLF-PJ.TO"
  const url = `https://finance.yahoo.com/quote/${ticker}?p=${ticker}`;
  const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  const contentText = res.getContentText();
  const ask = contentText.match(/ASK-value"\>(\d+.\d+)/);
  askVal = Number(ask[1])
  const bid = contentText.match(/BID-value"\>(\d+.\d+)/);
  bidVal = Number(bid[1])
  result = [bidVal, askVal]
  console.log(result)
  return result;
}

function yahooTest() {
  yahooBidAsk("SLF-PJ.TO")
}

function standardPrefToYahoo(ticker) {
  parts = ticker.split(".")
  result = parts[0] + "-P" + parts[2] + ".TO"
  return result
}
function standardPrefToGlobe(ticker) {
  parts = ticker.split(".")
  result = parts[0] + "-PR-" + parts[2] + "-T"
  return result
}
function testStandard() {
  console.log(standardPrefToYahoo("SLF.PR.J"))
  console.log(standardPrefToGlobe("SLF.PR.J"))
}

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Misha Menu')
      //.addItem('Say Hello', 'helloWorld')
      .addItem('Pop BidAsk', 'populateBidAskPrices')
      .addItem('Pop DivsAndDate', 'populateDivAndDate')
      addItem('Pop Both Fast', 'populateFast')
      .addToUi();
}
 
 function populateDivAndDate(){
  populateAskPrices(true)
 }

function populateBidAskPrices(){
  populateAskPrices(false)
 }
 function populateFast(){
  populateSheetParallel(true)
  populateSheetParallel(false)
 }


function populateAskPrices(bGetDivs) {
  var i
  var sheet = SpreadsheetApp.getActive().getSheetByName("Asks")
  var rangeData = sheet.getDataRange();
  var lastColumn = rangeData.getLastColumn();
  var lastRow =  Math.min(rangeData.getLastRow(), 99)
  //console.log("Last Row:", lastRow)
  var searchRange = sheet.getRange(1,1,lastRow,lastColumn-1)
  var numDataRows = lastRow -1 

  var numOutCols = bGetDivs ? 2 : 2
  var startCol = bGetDivs ? 4 : 2

  var outRange = sheet.getRange(2,startCol,numDataRows,numOutCols)

  var rangeValues = searchRange.getValues()
  var data = []
   // assume top row is headers, so start i at 1
   // Last row to access is zero based
  for (i = 1; i < lastRow; i++) {
    std_ticker = rangeValues[i][0]

    if (bGetDivs) {
      gticker = standardPrefToGlobe(std_ticker)
      fwdDiv = globeDivA(gticker)
      data.push([fwdDiv[0], fwdDiv[1]])
    }
    else { // bid/ask}
      yticker = standardPrefToYahoo(std_ticker)
      bidaskPrice = yahooBidAsk(yticker)
      data.push([bidaskPrice[0], bidaskPrice[1]])
    }
     if ((i % 5) == 0) {
       console.log("Processed ", i)
     }
   }
   //console.log("Num prices:", data.length)
   //console.log(data)

   outRange.setValues(data)
  return 66
}


function globeDivA(ticker) {
  //const ticker="SLF-PR-J-T"
  const url = `https://www.theglobeandmail.com/investing/markets/stocks/${ticker}/dividends`;
  const res = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
  const contentText = res.getContentText();
  const price = contentText.match(/dividendRateForward" type="float" value="(\d+.\d+)/);
  const priceVal = Number(price[1])
  const lastDivDate = contentText.match(/name="dividend" type="float" value="([a-z 0-9\/\.]+)"/);
  const lastDivTxt = parseGlobeData(lastDivDate[1])
  
  return [priceVal, lastDivTxt];
}

function testGlobe() {
  console.log(globeDivA("SLF-PR-J-T"))
}

Date.prototype.addDays = function(days) {
    var date = new Date(this.valueOf());
    date.setDate(date.getDate() + days);
    return date;
}

// input is: "xyz on DD/MM/YY"; output is DD/MM, with 3 months added to month, wrapped.
function parseGlobeData(foo) {
  
  var baz = foo.search(" on ")
  var rest = foo.substr(baz+4)
  var pieces = rest.split("/")
  var month = Number(pieces[0])-1 // javascript treats months funny
  var year = Number(pieces[2])
  var day = Number(pieces[1])
  var today = new Date()
  var exDivDate = new Date(year+2000, month, day)
  // console.log("sampled: ", exDivDate)

  if (exDivDate < today) {
  // if before today, add 3 months
      exDivDate = exDivDate.addDays(91)
  }
  //console.log("added: ", exDivDate)
  // console.log(exDivDate.getFullYear(), exDivDate.getMonth()+1, exDivDate.getDate())

var result =  (exDivDate.getFullYear()-2000).toString() + "-" +
              (exDivDate.getMonth()+1).toString().padStart(2,0) + "-" + 
              (exDivDate.getDate()).toString().padStart(2,0) 

return result
}

function testDivDate() {
    console.log(parseGlobeData("xx on 1/12/22"), " expect 22-04-12")
    console.log(parseGlobeData("yy on 11/27/22"), "expect 23-02-27" )
    console.log(parseGlobeData("zz on 11/2/22"), "expect 23-02-02" )
}

function parseGlobeDivA(res) {
  const contentText = res.getContentText();
  const price = contentText.match(/dividendRateForward" type="float" value="(\d+.\d+)/);
  const priceVal = Number(price[1])
  const lastDivDate = contentText.match(/name="dividend" type="float" value="([a-z 0-9\/\.]+)"/);
  const lastDivTxt = parseGlobeData(lastDivDate[1])
  
  return [priceVal, lastDivTxt];
}

function parseYahooBidAsk(res) {
  const contentText = res.getContentText();
  const ask = contentText.match(/ASK-value"\>(\d+.\d+)/);
  askVal = Number(ask[1])
  const bid = contentText.match(/BID-value"\>(\d+.\d+)/);
  bidVal = Number(bid[1])
  result = [bidVal, askVal]
  console.log(result)
  return result;
}


var  testTickers = ["SLF-PR-J-T", "TRP-PR-H-T" , "TRP-PR-F-T" , "FN-PR-B-T"]

function testParallel() {
     parallelFetchGlobe(testTickers)
}

// TODO: refactor for tidy
function parallelFetchGlobe(prefTickers) {
  urlList = prefTickers.map(ticker => `https://www.theglobeandmail.com/investing/markets/stocks/${ticker}/dividends`)
  // console.log(urlList)
  const fetchResult =  UrlFetchApp.fetchAll(urlList);
  results = fetchResult.map(parseGlobeDivA)
  return results
}
function parallelFetchYahoo (prefTickers) {
  urlList = prefTickers.map(ticker => `https://finance.yahoo.com/quote/${ticker}?p=${ticker}`)

  // console.log(urlList)
  const fetchResult =  UrlFetchApp.fetchAll(urlList);
  results = fetchResult.map(parseYahooBidAsk)
  return results
}

function populateSheetParallel(bGetDivs) {
  var i
  var sheet = SpreadsheetApp.getActive().getSheetByName("Asks")
  var rangeData = sheet.getDataRange();
  var lastColumn = rangeData.getLastColumn();
  var lastRow =  Math.min(rangeData.getLastRow(), 99)
  //console.log("Last Row:", lastRow)
  var searchRange = sheet.getRange(1,1,lastRow,lastColumn-1)

  var numDataRows = lastRow -1 

  var numOutCols = bGetDivs ? 2 : 2
  var startCol = bGetDivs ? 4 : 2

  var outRange = sheet.getRange(2,startCol,numDataRows,numOutCols)

  var rangeValues = searchRange.getValues()
  var data = []
   // assume top row is headers, so start i at 1
   // Last row to access is zero based

  // build list of tickers
  var tickerList = []
  for (i = 1; i < lastRow; i++) {
    std_ticker = rangeValues[i][0]
    tickerList.push(std_ticker)
  }

  var result 
  if (bGetDivs) {
     customTickerList = tickerList.map(standardPrefToGlobe)
     result = parallelFetchGlobe(customTickerList)
  }
  else {
     customTickerList = tickerList.map(standardPrefToYahoo)
     result = parallelFetchYahoo(customTickerList)
  }
 
 // console.log(result)
  outRange.setValues(result)
  return
}


