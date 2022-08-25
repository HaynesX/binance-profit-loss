
from binance.client import Client
import time
import telebot
import datetime
import json
import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials

TELEGRAM_SECRET_KEY = os.getenv('TELEGRAM_SECRET_KEY')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')


bot = telebot.TeleBot(TELEGRAM_SECRET_KEY)

try:
    client = Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET_KEY, testnet=False)
except Exception as e:
    bot.send_message("-734646829", f"Client not connecting. {e}", disable_web_page_preview=True)





scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("pnlData/haynes-bybit-b58869a98ed4.json", scope)
googleClient = gspread.authorize(creds)
sheet = googleClient.open("Trades - Bybit").worksheet("Phil Binance 2 Min Long")
dailyProfitSheet = googleClient.open("Trades - Bybit").worksheet("Phil Binance Daily Profit Log")







def main():
    time.sleep(10)



    with open('pnlData/data.json') as json_file:
        mainTradesDictionary = json.load(json_file)
        listOfKeys = list(mainTradesDictionary.keys())
        start_time = int(listOfKeys[-1])






    trades = client.get_my_trades(symbol='BTCUSDT', startTime=start_time+1)
    print(trades)

    if len(trades) == 0:
        return
    
    dailyDates = dailyProfitSheet.col_values(1)
    dailyProfits = dailyProfitSheet.col_values(2)

    dailyCurrentDict = {}

    for index, eachDateProfitList in enumerate(zip(dailyDates, dailyProfits), start=1):
        if index == 1:
            continue
    
        dailyCurrentDict[eachDateProfitList[0]] = {"Profit": float(eachDateProfitList[1]), "Cell": f"B{index}"}

    tradesDictionary = {}
    newTradesFound = []

    for eachTrade in trades:
        if eachTrade["time"] not in mainTradesDictionary:
            if eachTrade["time"] not in tradesDictionary:
                newTradesFound.append(eachTrade["time"])
                tradesDictionary[eachTrade["time"]] = {}
                tradesDictionary[eachTrade["time"]]["raw_trades"] = [eachTrade]
            else:
                tradesDictionary[eachTrade["time"]]["raw_trades"].append(eachTrade)


    for eachTradeTimestamp in tradesDictionary:
        allRawTrades = tradesDictionary[eachTradeTimestamp]["raw_trades"]
        side = ""
        executionPricesToQuantity = []
        totalOrderSize = 0

        for index, eachRawTrade in enumerate(allRawTrades, start=0):
            if index == 0:
                if eachRawTrade["isBuyer"] == False:
                    side = "Sell"
                else:
                    side = "Buy"
            
            executionPricesToQuantity.append([float(eachRawTrade["price"]), float(eachRawTrade["quoteQty"])])
            totalOrderSize += float(eachRawTrade["quoteQty"])

            # total order size / (quantity A/execution price A + order size B/execution price B +…. etc etc)
        
        partTwoCalculation = 0

        for eachExecPriceToQuantity in executionPricesToQuantity:
            partTwoCalculation += (eachExecPriceToQuantity[1] / eachExecPriceToQuantity[0])
        
        averageExecutionPrice = totalOrderSize / partTwoCalculation

        tradesDictionary[eachTradeTimestamp]["side"] = side
        tradesDictionary[eachTradeTimestamp]["totalOrderSize"] = round(totalOrderSize, 7)
        tradesDictionary[eachTradeTimestamp]["avgExecPrice"] = round(averageExecutionPrice, 8)

    oldTradesKeys = list(mainTradesDictionary.keys())
    oldTradesKeys.reverse()

    # newTradesFound.reverse() #newest trade first


    googleSheetRows = []
    telegramMessages = []

    dailyNewDict = {}


    for eachNewTradeTimestamp in newTradesFound:
        newTrade = tradesDictionary[eachNewTradeTimestamp]
        if newTrade["side"] == "Buy":
            

            previousSellTimestamp = oldTradesKeys[0]
            previousSell = mainTradesDictionary[previousSellTimestamp]

            
            currentBalance = previousSell["current_balance"] - newTrade["totalOrderSize"]
            previousBalance = previousSell["current_balance"]



            newTrade["current_balance"] = currentBalance
            newTrade["previous_balance"] = previousBalance


            mainTradesDictionary[eachNewTradeTimestamp] = newTrade
            oldTradesKeys.insert(0, eachNewTradeTimestamp)
            # add to google sheet list of new rows

            created_at = datetime.datetime.fromtimestamp(eachNewTradeTimestamp / 1000)
            created_at_string = created_at.strftime("%d/%m/%Y %H:%M:%S")




            telegramMessage = f"""
    <b>Trade Opened</b>
                        
    Side: <b>Buy</b>
    Entry: <b>{round(newTrade["avgExecPrice"], 2)}</b>
    Qty: <b>{round(newTrade["totalOrderSize"], 2)}</b>

    <b>{created_at_string}</b>
    """

            telegramMessages.append(telegramMessage)

            








        else:
            previousBuyTimestamp = oldTradesKeys[0]
            previousBuy = mainTradesDictionary[previousBuyTimestamp]

            previousSellTimestamp = oldTradesKeys[1]
            previousSell = mainTradesDictionary[previousSellTimestamp]

            # work out p&l

            entryPrice = previousBuy["avgExecPrice"]
            exitPrice = newTrade["avgExecPrice"]

            currentBalance = previousBuy["current_balance"] + newTrade["totalOrderSize"]
            PnL_USD = currentBalance - previousSell["current_balance"]
            PnL_Percentage = round(((currentBalance - previousSell["current_balance"]) / previousSell["current_balance"]) * 100, 3)

            previousBalance = previousBuy["current_balance"]
            previousSellBalance = previousSell["current_balance"]

            firstTradeBalance = mainTradesDictionary[oldTradesKeys[-1]]["current_balance"]

            cumulative_pnl_percentage = round(((currentBalance - firstTradeBalance) / firstTradeBalance) * 100, 3)
            cumulative_pnl_dollars = currentBalance - firstTradeBalance

            winOrLoss = ""
            if PnL_USD >= 0:
                winOrLoss = "Win"
            else:
                winOrLoss = "Loss"

            newTrade["current_balance"] = currentBalance
            newTrade["previous_balance"] = previousBalance
            newTrade["previous_sell_balance"] = previousSellBalance
            newTrade["PnL_USD"] = PnL_USD
            newTrade["PnL_Percentage"] = PnL_Percentage
            newTrade["PnL_USD_Cumulative"] = cumulative_pnl_dollars
            newTrade["PnL_Percentage_Cumalative"] = cumulative_pnl_percentage
            newTrade["entry"] = entryPrice
            newTrade["exit"] = exitPrice
            newTrade["winOrLoss"] = winOrLoss

            created_at = datetime.datetime.fromtimestamp(eachNewTradeTimestamp / 1000)
            created_at_string = created_at.strftime("%d/%m/%Y %H:%M:%S")

            created_at_day_month_year = created_at.strftime("%d/%m/%Y")

            if created_at_day_month_year in dailyCurrentDict:
                dailyCurrentDict[created_at_day_month_year]["Profit"] += PnL_Percentage
            else:
                if created_at_day_month_year in dailyNewDict:
                    dailyNewDict[created_at_day_month_year]["Profit"] += PnL_Percentage
                else:
                    dailyNewDict[created_at_day_month_year] = {"Profit": PnL_Percentage}

            

            
            


            googleSheetRows.append([created_at_string, newTrade["side"], entryPrice, exitPrice, PnL_USD, PnL_Percentage, cumulative_pnl_dollars, cumulative_pnl_percentage, previousBalance, previousSellBalance, currentBalance, winOrLoss, "", entryPrice, "", "", "", PnL_Percentage, "=(Q4-R4)/ABS(R4)"])


            telegramMessage = f"""
    <b>Trade Closed</b>
                        
    Side: <b>Sell</b>
    Entry: <b>{round(entryPrice, 3)}</b>
    Exit: <b>{round(exitPrice, 3)}</b>
    Qty: <b>{round(newTrade["totalOrderSize"], 4)}</b>
    P&L%: <b>{PnL_Percentage}</b>

    <b>{created_at_string}</b>
    <b><a href="https://docs.google.com/spreadsheets/d/1gNFpHEs0YXCYgrdGnk-5b8DuOLrwBKtDkfxxRK0GgVc/edit#gid=1422884573">Google Sheet</a></b>
    """

            telegramMessages.append(telegramMessage)


            ### Send Telegram Message Here






            mainTradesDictionary[eachNewTradeTimestamp] = newTrade
            oldTradesKeys.insert(0, eachNewTradeTimestamp)
            # add to google sheet list of new rows


    dailyProfitNewRows = []
    for eachKey in dailyNewDict:
        dailyProfitNewRows.append([eachKey, dailyNewDict[eachKey]["Profit"], "", "=B2-C2"])
    

    dailyProfitBatchUpdateList = []
    for eachKey in dailyCurrentDict:
        dailyProfitBatchUpdateList.append({'range': dailyCurrentDict[eachKey]["Cell"], 'values': [[dailyCurrentDict[eachKey]["Profit"]]]})


    if len(googleSheetRows) > 0:
        print("New P&L Found. Adding to Google Sheet.")
        googleSheetRows.reverse()
        sheet.insert_rows(googleSheetRows, row=4, value_input_option='USER_ENTERED')
        googleSheetRows.reverse()
        dailyProfitSheet.batch_update(dailyProfitBatchUpdateList)
        dailyProfitNewRows.reverse()
        dailyProfitSheet.insert_rows(dailyProfitNewRows, row=2, value_input_option='USER_ENTERED')
    
    for eachTelegramMessage in telegramMessages:
        bot.send_message(TELEGRAM_CHAT_ID, eachTelegramMessage, parse_mode="HTML", disable_web_page_preview=True)
        time.sleep(4.5)

    time.sleep(4)
            
    with open("pnlData/data.json", "w") as outfile:
        json.dump(mainTradesDictionary, outfile)





if __name__ == "__main__":
    bot.send_message("-734646829", "Bot Starting", disable_web_page_preview=True)
    while True:
        try:
            main()
        except Exception as e:
            bot.send_message("-734646829", e, disable_web_page_preview=True)

            time.sleep(10)
       