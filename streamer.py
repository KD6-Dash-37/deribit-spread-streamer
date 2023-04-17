import json
import websockets
import asyncio
import curses


with open("settings.json") as json_file:
    config = json.load(json_file)

end_point = config["end_point"]

channels = [f"quote.{instrument}" for instrument in config["instruments"]]

msg = {
    "jsonrpc": "2.0",
    "method": "public/subscribe",
    "id": 42,
    "params": {
        "channels": channels
        }
    }


def parse_response(response: str) -> dict:

    response = json.loads(response)

    params = response.get("params", None)

    try:
        channel = params.get("channel")

        instrument = channel.split(".")[-1]

        data = params.get("data")

        best_bid_price = data.get("best_bid_price")

        best_ask_price = data.get("best_ask_price")

        parsed_response = {
            "instrument": instrument,
            "best_bid_price": best_bid_price,
            "best_ask_price": best_ask_price,
        }

        return parsed_response

    except AttributeError:
        pass


def display_spread(stdscr, leg_b_name, bid_spread, ask_spread):
    stdscr.clear()
    stdscr.attron(curses.color_pair(1))
    stdscr.addstr(0, 0, "\t\tBid\tAsk")

    level = ""

    # RED if the ask is greater than defined rich price color the quotes
    if ask_spread > config["rich"]:
        stdscr.attron(curses.color_pair(2))
        level = "RICH"

    # PURPLE if the ask is greater than fair value but less than rich
    elif ask_spread > config["fair_value"]:
        stdscr.attron(curses.color_pair(3))
        level = "FAIR VALUE"

    # GREEN if the ask less than dirt cheap
    elif ask_spread < config["dirt_cheap"]:
        stdscr.attron(curses.color_pair(5))
        level = "DIRT CHEAP"

    # PINK if the ask is less greater than dirt cheap but less than cheap
    elif ask_spread < config["cheap"]:
        stdscr.attron(curses.color_pair(4))
        level = "CHEAP"

    # WHITE otherwise
    else:
        stdscr.attron(curses.color_pair(1))

    stdscr.addstr(1, 0, f"{leg_b_name}\t{bid_spread}\t{ask_spread}\t{level}")
    stdscr.refresh()


async def call_api(msg):

    leg_a, leg_b = config["leg_a"], config["leg_b"]
    leg_a_bid, leg_b_bid = None, None
    leg_a_ask, leg_b_ask = None, None

    stdscr = curses.initscr()
    curses.start_color()

    BACKGROUND = curses.COLOR_BLACK

    # WHITE with black background
    curses.init_pair(1, curses.COLOR_WHITE, BACKGROUND)
    # RED with black background
    curses.init_pair(2, curses.COLOR_RED, BACKGROUND)
    # PURPLE with black background
    curses.init_pair(3, curses.COLOR_MAGENTA, BACKGROUND)

    # Initialise PINK color
    curses.init_color(6, 215, 0, 135)
    # PINK with black background
    curses.init_pair(4, 6, BACKGROUND)

    # GREEN with black background
    curses.init_pair(5, curses.COLOR_GREEN, BACKGROUND)

    curses.noecho()
    curses.cbreak()

    async with websockets.connect(end_point) as websocket:

        await websocket.send(msg)

        while websocket.open:

            response = await websocket.recv()

            parsed_response = parse_response(response=response)

            try:
                if parsed_response["instrument"] == leg_a:

                    leg_a_bid = parsed_response["best_bid_price"]
                    leg_a_ask = parsed_response["best_ask_price"]
                    # print(leg_a_bid)

                elif parsed_response["instrument"] == leg_b:
                    leg_b_bid = parsed_response["best_bid_price"]
                    # print(leg_b_bid)
                    leg_b_ask = parsed_response["best_ask_price"]

            except TypeError:
                pass

            if all([leg_a_bid, leg_b_bid, leg_a_ask, leg_b_ask]):
                bid_spread = leg_b_bid - leg_a_bid
                ask_spread = leg_b_ask - leg_a_ask

                display_spread(
                    stdscr=stdscr,
                    leg_b_name=leg_b,
                    bid_spread=bid_spread,
                    ask_spread=ask_spread
                    )

asyncio.run(call_api(json.dumps(msg)))
