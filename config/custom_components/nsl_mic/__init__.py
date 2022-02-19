from lib2to3.pytree import convert
import os
from typing import Optional
import speech_recognition as sr
import requests
import webbrowser
import logging
from gtts import gTTS
import json
import subprocess
from config.custom_components.nsl_mic import constants
from geopy.geocoders import Nominatim
import pandas as pd
import datetime
import pytz

DOMAIN = "nsl_mic"

ATTR_NAME = "name"
DEFAULT_NAME = "Mic"
logger = logging.getLogger()


def setup(hass, config):
    """Set up is called when Home Assistant is loading our component."""

    def convert_text_to_speech(text):
        logging.info("Converting text to speech")
        myobj = gTTS(text=text, lang="en", slow=False)
        myobj.save("audio.mp3")
        subprocess.run(["/usr/bin/mpg321", "audio.mp3"], capture_output=True)
        os.remove("audio.mp3")
        return True

    def record(recognizer):
        with sr.Microphone() as source:
            # logging.info("Adjusting noise ")
            # recognizer.adjust_for_ambient_noise(source, duration=1)
            logging.info("Recording started")
            recorded_audio = recognizer.listen(source)
            logging.info("Done recording")
            text = ""
            try:
                logging.info("Recognizing the text")
                text = recognizer.recognize_google(recorded_audio, language="en-IN")
                logging.info("Decoded Text : {}".format(text))
            except Exception as ex:
                print(ex)
        return text

    def create_social_user(*argv):
        recognizer = argv[0]
        convert_text_to_speech("Please provide your email id.")
        email_text = record(recognizer)
        convert_text_to_speech("Please provide tenant name.")
        tenant_name = record(recognizer)
        url = "http://127.0.0.1:1234/createsocialuser"
        data = {"email": email_text, "tenant_name": tenant_name}
        response = requests.post(url, json=data)
        logging.info("Response status code" + str(response.status_code))
        response_text = json.loads(response.text)["message"]
        return response_text

    def order_pizza(recognizer, username, password, tenant_name):
        def get_current_location():
            current_location = ""
            # importing modules

            # calling the nominatim tool
            geoLoc = Nominatim(user_agent="GetLoc")

            # passing the coordinates
            locname = geoLoc.reverse(constants.CURR_ADDRESS_COORD)

            # printing the address/location name
            print(locname.address)
            current_location = locname.address
            return current_location

        def get_delivery_location(recognizer):
            is_correct_address = False
            current_location = get_current_location()
            curr_loc = current_location.split(",")
            if constants.HOME_ADDRESS.find(curr_loc[-2]) != -1:
                convert_text_to_speech(
                    "You are at your home. Do you want me to deliver the pizza here?"
                )
                ans = record(recognizer)
                if ans.lower() == "yes":
                    customer_address = constants.HOME_ADDRESS
                elif ans.lower() == "no":
                    customer_address = ""
            elif constants.WORK_ADDRESS.find(curr_loc[-2]) != -1:
                convert_text_to_speech(
                    "You are at your workplace. Do you want me to deliver the pizza here?"
                )
                ans = record(recognizer)
                if ans.lower() == "yes":
                    customer_address = constants.WORK_ADDRESS
                elif ans.lower() == "no":
                    customer_address = ""

            if customer_address == "":
                convert_text_to_speech(
                    "Please tell where should I get the pizza delivered?"
                )
                customer_address = record(recognizer)
                if customer_address.lower() == "cancel order":
                    customer_address = ""
                    convert_text_to_speech("Order cancelled")
                # while not is_correct_address:
                #     convert_text_to_speech(questions[0])
                #     customer_address = record(recognizer)
                #     if customer_address.lower() == "home":
                #         answers.append(constants.HOME_ADDRESS)
                #         is_correct_address = True
                #     elif customer_address.lower() == "work":
                #         answers.append(constants.WORK_ADDRESS)
                #         is_correct_address = True
                #     else:
                #         convert_text_to_speech("Invalid address.")
                #         if customer_address.lower() == "cancel order":
                #             convert_text_to_speech("Order cancelled")
                #             return
            return customer_address

        def get_pizza_size(recognizer, username, password, tenant_name):
            size = ""
            url = "http://127.0.0.1:1234/getmembercount"
            data = {
                "username": username,
                "password": password,
                "tenant_name": tenant_name,
            }
            logging.info("getting member count")
            response = requests.get(url, json=data)
            print(response.json())
            count = response.json()["message"]
            convert_text_to_speech(
                "Since you are in a meeting with " + count + " people"
            )
            count = int(count)
            if count <= 2:
                size = "Small"
                text = "1"
            elif count > 2 and count <= 4:
                size = "Medium"
                text = "2"
            else:
                size = "Large"
                text = "3"
            convert_text_to_speech("Would you like to order a " + size + " pizza?")
            ans = record(recognizer)
            if ans.lower() == "no":
                convert_text_to_speech(
                    "Please tell what size pizza would you like? Say one for small, two for medium, three for large"
                )
                text = record(recognizer)
            return text

        questions = [
            "Please provide your address. Say home or work.",
            "Which pizza would you like to order? Say one for Margherita, two for peppy paneer, three for chicken fiesta",
            "",
            "What toppings would you like? Say one for Onion, two for Mushroom, three for Corn",
            "What crust would you prefer? Say one for thin crust, two for cheese burst, three for cracker crust",
            "What cheese type would you like? Say one for regular cheese, two for Mozzarella cheese",
            "Would you like to add another pizza to this order? Say yes or no.",
        ]

        values = [
            {"1": "Margherita", "2": "Peppy paneer", "3": "Chicken Fiesta"},
            {"1": "Small", "2": "Medium", "3": "Large"},
            {"1": "Onion", "2": "Mushroom", "3": "Corn"},
            {"1": "Thin crust", "2": "Cheese burst", "3": "Cracker crust"},
            {"1": "Regular cheese", "2": "Mozzarella cheese"},
            {"1": "Card", "2": "Cash", "3": "UPI"},
        ]

        pizza_cost = {"1": "100", "2": "150", "3": "200"}

        answers = []
        convert_text_to_speech(
            " I see that you ordered a small Margherita pizza with corn topping and mozarella cheeseburst crust"
        )
        convert_text_to_speech(
            "Do you wish to continue with your previous order or do you want to place a new order?"
        )
        continue_prev_order = record(recognizer)

        answers.append(username)
        is_another_pizza = True
        total_cost = 0
        total_number_of_pizzas = 0
        while is_another_pizza:
            total_number_of_pizzas = total_number_of_pizzas + 1
            i = 1
            while i < len(questions):
                if questions[i] != "":
                    convert_text_to_speech(questions[i])
                if i == 2:
                    text = get_pizza_size(recognizer, username, password, tenant_name)
                else:
                    text = record(recognizer)
                if text.lower() == "cancel order":
                    convert_text_to_speech("Order cancelled")
                    return
                if text.lower() == "tu":
                    text = "2"
                if (
                    text != "1"
                    and text != "2"
                    and text != "3"
                    and text != "yes"
                    and text != "no"
                ):
                    convert_text_to_speech("Sorry not able to understand")
                    continue
                if i == 1:
                    if text == "1":
                        total_cost = total_cost + int(pizza_cost["1"])
                    elif text == "2":
                        total_cost = total_cost + int(pizza_cost["2"])
                    else:
                        total_cost = total_cost + int(pizza_cost["3"])
                    logging.info("Total cost: " + str(total_cost))

                if i != len(questions) - 1:
                    answers.append(values[i - 1][text])
                if i == len(questions) - 1 and text.lower() == "no":
                    is_another_pizza = False
                i = i + 1

        convert_text_to_speech("Total cost of the order is" + str(total_cost))
        answers.append(str(total_cost))

        customer_address = get_delivery_location(recognizer)
        if customer_address != "":
            answers.insert(0, customer_address)

        convert_text_to_speech("Please confirm the order. Say yes or no")
        user_confirmation = record(recognizer)

        if user_confirmation.lower() == "yes":
            convert_text_to_speech(
                "What payment method would you prefer? Say one for Card, two for cash, three for U P I"
            )
            text = record(recognizer)
            if text.lower() == "cancel order":
                convert_text_to_speech("Order cancelled")
                return
            if text.lower() == "tu":
                text = "2"
            answers.append(values[5][text])
            convert_text_to_speech("Please say the pin to confirm the order")
            text = record(recognizer)
            if text.lower() == "cancel order":
                convert_text_to_speech("Order cancelled")
                return
            for i in range(1, 4):
                if text != constants.PIN:
                    convert_text_to_speech(
                        "Invalid Pin. Please say correct pin. "
                        + str(3 - i)
                        + " more chances left"
                    )
                    if i == 3:
                        convert_text_to_speech(
                            "Payment failed. Order cancelled due to invalid pin"
                        )
                        return
                    text = record(recognizer)
                    if text.lower() == "cancel order":
                        convert_text_to_speech("Order cancelled")
                        return
                else:
                    break
        else:
            convert_text_to_speech("Order Cancelled")
            return

        convert_text_to_speech("Payment successful")
        convert_text_to_speech("Would you like to track your order? Say yes or no")
        text = record(recognizer)
        if text.lower() == "yes":
            answers.append(True)
        else:
            answers.append(False)

        url = "http://127.0.0.1:1234/orderpizza"
        # data = {
        #     "customer_address": answers[0],
        #     "customer_name": answers[1],
        #     "pizza_details": [],
        #     "total_order_cost": answers[len(answers) - 4],
        #     "payment_method": answers[len(answers) - 3],
        #     "is_payment_success": answers[len(answers) - 2],
        #     "track_order": answers[len(answers) - 1],
        #     "auth_details":{"username":username, "password":password, "tenant_name":tenant_name}
        # }
        data = {
            "order_details": answers,
            "auth_details": {
                "username": username,
                "password": password,
                "tenant_name": tenant_name,
            },
        }
        # j = 2
        # for i in range(0, total_number_of_pizzas):
        #     data["pizza_details"].append({})
        #     data["pizza_details"][i]["pizza_name"] = answers[j]
        #     j = j + 1
        #     data["pizza_details"][i]["pizza_size"] = answers[j]
        #     j = j + 1
        #     data["pizza_details"][i]["pizza_toppings"] = answers[j]
        #     j = j + 1
        #     data["pizza_details"][i]["pizza_crust"] = answers[j]
        #     j = j + 1
        #     data["pizza_details"][i]["cheese_type"] = answers[j]
        #     j = j + 1

        print(data)
        response = requests.post(url, json=data)
        logging.info("Response status code" + str(response.status_code))
        response_text = json.loads(response.text)["message"]
        convert_text_to_speech("Order dispatched")
        convert_text_to_speech("Order delivered. Enjoy your meal")
        return response_text

    def order_pizza_new(*argv):
        recognizer = argv[0]
        username = argv[1]
        password = argv[2]
        tenant_name = argv[3]
        df = pd.read_csv("config/custom_components/nsl_mic/PreviousOrderDetails.csv")
        values = [
            ["Peppy paneer", "Chicken Fiesta", "Margarita", "Margherita"],
            ["Small", "Medium", "Large"],
            ["Onion", "Mushroom", "Corn"],
            ["Thin crust", "Cheese burst", "Cracker crust"],
            ["Regular cheese", "Mozzarella cheese"],
            ["Card", "Cash", "UPI"],
        ]

        pizza_cost = {
            "Margherita": "100",
            "Peppy paneer": "150",
            "Chicken Fiesta": "200",
        }
        total_order_cost = 0

        def is_previous_order():
            # convert_text_to_speech(
            #     "Hey there, seems like someone is craving for a pizza. Let's quickly order a pizza together."
            # )
            previous_order_details = []
            for i in range(2, 7):
                previous_order_details.append(df.iloc[df.shape[0] - 1][i])
            print(previous_order_details)
            convert_text_to_speech(
                "I see that you ordered "
                + previous_order_details[1]
                + " "
                + previous_order_details[0]
                + " pizza with "
                + previous_order_details[4]
                + " "
                + previous_order_details[3]
                + " and "
                + previous_order_details[2]
                + " toppings before."
                + " Do you wish to continue the same order or like to order a new one?"
            )
            user_response = record(recognizer)
            user_response = preprocess_user_response(user_response)
            return user_response

        def preprocess_user_response(user_response, values_index=None):
            user_response = user_response.lower()
            if user_response == "cancel order":
                convert_text_to_speech("Order cancelled")
                return "Order cancelled"

            if values_index != None:
                for keyword in values[values_index]:
                    if user_response.find(keyword.lower()) != -1:
                        user_response = keyword
                        return user_response

            if (
                user_response.find("yes") == -1
                and user_response.find("no") == -1
                and user_response.find("continue") == -1
            ):
                convert_text_to_speech("Sorry not able to understand")
                return "Invalid"
            print(user_response)
            return user_response

        def get_member_count():
            url = "http://127.0.0.1:1234/getmembercount"
            data = {
                "username": username,
                "password": password,
                "tenant_name": tenant_name,
            }
            logging.info("getting member count")
            response = requests.get(url, json=data)
            count = response.json()["message"]
            logging.info("NSL Meeting member count: {}".format(count))
            return int(count)

        def get_pizza_name():
            nonlocal total_order_cost
            pizza_name = df["Pizza Name"].mode()
            convert_text_to_speech(
                "Okay. As always would you like to go with the "
                + pizza_name[0]
                + " or go with a new one?"
            )
            user_response = record(recognizer)
            user_response = preprocess_user_response(user_response)
            if user_response == "Order cancelled":
                return "Order cancelled"
            if user_response == "Invalid":
                return get_pizza_name()

            if user_response.find("yes") != -1:
                total_order_cost = 200
                return pizza_name[0]

            else:
                is_valid = False
                while is_valid == False:
                    convert_text_to_speech(
                        "In such case, which pizza would you like to order?"
                    )
                    user_response = record(recognizer)
                    user_response = preprocess_user_response(user_response, 0)
                    if user_response == "Order cancelled":
                        return "Order cancelled"
                    if user_response != "Invalid":
                        is_valid = True
            total_order_cost = pizza_cost[user_response]
            return user_response

        def get_pizza_size():
            member_count = get_member_count()
            member_count += 3
            pizza_size = ""
            if member_count < 2:
                pizza_size = "Small"
            elif member_count >= 2 and member_count < 4:
                pizza_size = "Medium"
            else:
                pizza_size = "Large"

            convert_text_to_speech(
                "As you are in a meeting of "
                + str(member_count)
                + ". Do you like to order "
                + pizza_size
                + " size pizza?"
            )
            user_response = record(recognizer)
            user_response = preprocess_user_response(user_response)
            if user_response == "Order cancelled":
                return "Order cancelled"
            if user_response == "Invalid":
                return get_pizza_size()
            if user_response.find("yes") != -1:
                return pizza_size
            else:
                is_valid = False
                while is_valid == False:
                    convert_text_to_speech(
                        "In such case, which pizza size would you like to order?"
                    )
                    user_response = record(recognizer)
                    user_response = preprocess_user_response(user_response, 1)
                    if user_response == "Order cancelled":
                        return "Order cancelled"
                    if user_response != "Invalid":
                        is_valid = True
            return user_response

        def get_pizza_toppings():
            pizza_toppings = df["Pizza Toppings"].mode()
            convert_text_to_speech(
                "Okay, how about the toppings. You liked "
                + pizza_toppings[0]
                + " the most. Do you wish to continue the same or wanna try a new topping?"
            )
            user_response = record(recognizer)
            user_response = preprocess_user_response(user_response)
            if user_response == "Order cancelled":
                return "Order cancelled"
            if user_response == "Invalid":
                return get_pizza_toppings()
            if user_response.find("yes") != -1:
                return pizza_toppings[0]
            else:
                is_valid = False
                while is_valid == False:
                    convert_text_to_speech(
                        "In such case, which pizza topping would you like?"
                    )
                    user_response = record(recognizer)
                    user_response = preprocess_user_response(user_response, 2)
                    if user_response == "Order cancelled":
                        return "Order cancelled"
                    if user_response != "Invalid":
                        is_valid = True
            return user_response

        def get_pizza_crust():
            pizza_crust = df["Pizza Crust"].mode()
            convert_text_to_speech(
                "Well, you prefer "
                + pizza_crust[0]
                + " usually. So is that fine or you want to change?"
            )
            user_response = record(recognizer)
            user_response = preprocess_user_response(user_response)
            if user_response == "Order cancelled":
                return "Order cancelled"
            if user_response == "Invalid":
                return get_pizza_toppings()
            if user_response.find("yes") != -1:
                return pizza_crust[0]
            else:
                is_valid = False
                while is_valid == False:
                    convert_text_to_speech("What crust would you prefer?")
                    user_response = record(recognizer)
                    user_response = preprocess_user_response(user_response, 3)
                    if user_response == "Order cancelled":
                        return "Order cancelled"
                    if user_response != "Invalid":
                        is_valid = True
            return user_response

        def get_cheese_type():
            is_valid = False
            while is_valid == False:
                convert_text_to_speech("What cheese type would you like?")
                user_response = record(recognizer)
                user_response = preprocess_user_response(user_response, 4)
                if user_response == "Order cancelled":
                    return "Order cancelled"
                if user_response != "Invalid":
                    is_valid = True
            return user_response

        def get_pizza_count():
            count = get_member_count()
            count += 3
            pizza_count = 0
            if count < 2:
                pizza_count = 1
            elif count >= 2 and count < 6:
                pizza_count = 2
            else:
                pizza_count = 4
            pizza_count = str(pizza_count)
            convert_text_to_speech(
                "As you are in a meeting of "
                + str(count)
                + ", would you like to order "
                + pizza_count
                + " pizzas?"
            )
            user_response = record(recognizer)
            user_response = preprocess_user_response(user_response)
            if user_response == "Order cancelled":
                return "Order cancelled"
            if user_response == "Invalid":
                return get_pizza_count()
            if user_response.find("yes") != -1:
                return pizza_count
            else:
                is_valid = False
                while is_valid == False:
                    convert_text_to_speech("How many pizzas would you like to add?")
                    user_response = record(recognizer)
                    user_response = preprocess_user_response(user_response)
                    if user_response == "Order cancelled":
                        return "Order cancelled"
                    if user_response != "Invalid":
                        is_valid = True
            nonlocal total_order_cost
            total_order_cost = total_order_cost * int(count)
            return user_response

        def get_current_location():
            current_location = ""
            geoLoc = Nominatim(user_agent="GetLoc")
            locname = geoLoc.reverse(constants.CURR_ADDRESS_COORD)
            print(locname.address)
            current_location = locname.address
            return current_location

        def get_delivery_location(recognizer):
            is_correct_address = False
            current_location = get_current_location()
            curr_loc = current_location.split(",")
            if constants.HOME_ADDRESS.find(curr_loc[-2]) != -1:
                convert_text_to_speech(
                    "You are at your home. Do you want me to deliver the pizza here?"
                )
                ans = record(recognizer)
                if ans.lower() == "yes":
                    customer_address = constants.HOME_ADDRESS
                elif ans.lower() == "no":
                    customer_address = ""
            elif constants.WORK_ADDRESS.find(curr_loc[-2]) != -1:
                convert_text_to_speech(
                    "You are at your workplace. Do you want me to deliver the pizza here?"
                )
                ans = record(recognizer)
                if ans.lower() == "yes":
                    customer_address = constants.WORK_ADDRESS
                elif ans.lower() == "no":
                    customer_address = ""

            if customer_address == "":
                convert_text_to_speech(
                    "Please tell where should I get the pizza delivered?"
                )
                customer_address = record(recognizer)
                if customer_address.lower() == "cancel order":
                    customer_address = ""
                    convert_text_to_speech("Order cancelled")

            return customer_address

        is_previous_order = is_previous_order()
        answers = []
        answers.append(username)
        if is_previous_order.find("continue") == -1:
            answers.append(get_pizza_name())
            answers.append(get_pizza_size())
            answers.append(get_pizza_toppings())
            answers.append(get_pizza_crust())
            answers.append(get_cheese_type())
            answers.append(str(get_pizza_count()))
            answers.append(str(total_order_cost))
            answers.insert(0, get_delivery_location(recognizer))
        else:
            total_order_cost = df.iloc[df.shape[0] - 1][9]
            answers.insert(0, get_delivery_location(recognizer))
            for i in range(2, 9):
                answers.append(str(df.iloc[df.shape[0] - 1][i]))

        convert_text_to_speech("Total cost of the order is" + str(total_order_cost))
        convert_text_to_speech("Please confirm the order. Say yes or no")
        user_confirmation = record(recognizer)

        if user_confirmation.lower() == "yes":
            convert_text_to_speech("What payment method would you prefer?")
            user_response = record(recognizer)
            user_response = preprocess_user_response(user_response, 5)
            answers.append(user_response)
            convert_text_to_speech("Please say the pin to confirm the order")
            text = record(recognizer)
            if text.lower() == "cancel order":
                convert_text_to_speech("Order cancelled")
                return
            for i in range(1, 4):
                if text != constants.PIN:
                    convert_text_to_speech(
                        "Invalid Pin. Please say correct pin. "
                        + str(3 - i)
                        + " more chances left"
                    )
                    if i == 3:
                        convert_text_to_speech(
                            "Payment failed. Order cancelled due to invalid pin"
                        )
                        return
                    text = record(recognizer)
                    if text.lower() == "cancel order":
                        convert_text_to_speech("Order cancelled")
                        return
                else:
                    break
        else:
            convert_text_to_speech("Order Cancelled")
            return

        convert_text_to_speech("Payment successful")
        convert_text_to_speech("Would you like to track your order? Say yes or no")
        text = record(recognizer)
        if text.lower() == "yes":
            answers.append(True)
        else:
            answers.append(False)

        url = "http://127.0.0.1:1234/orderpizza"
        data = {
            "order_details": answers,
            "auth_details": {
                "username": username,
                "password": password,
                "tenant_name": tenant_name,
            },
        }

        print(data)
        response = requests.post(url, json=data)
        logging.info("Response status code" + str(response.status_code))
        response_text = json.loads(response.text)["message"]
        convert_text_to_speech("Your order will reach in 15-20 minutes.")
        return response_text

    def open_marketplace():
        return 0

    def get_day_stage():
        current_time_hour = datetime.datetime.now(pytz.timezone("Asia/Kolkata")).hour
        day_stage = ""
        if current_time_hour >= 6 and current_time_hour < 14:
            day_stage = "Morning"
        elif current_time_hour >= 14 and current_time_hour < 18:
            day_stage = "Afternoon"
        else:
            day_stage = "Evening"
        logging.info("Day stage: " + day_stage)
        return day_stage

    def execute_genie(*argv):
        logging.info(f"question is ----- {argv[4]}")
        url = "http://localhost:3000/api/converse"
        data = {"command": {"type": "command", "text": argv[4]}}
        x = requests.post(url, json=data)
        y = json.loads(x.text)
        y = y["messages"]

        answer = ""
        for i in y:
            if i["type"] == "text":
                if len(i["text"]) == 0:
                    answer = "sorry"
                    break
                if answer == "":
                    answer = i["text"]
            elif i["type"] == "rdl":
                if "callback" in i["rdl"]:
                    answer = answer + " Url is " + i["rdl"]["callback"]
                elif "webCallback" in i["rdl"]:
                    answer = answer + " Url is " + i["rdl"]["webCallback"]
        logging.info(f"answer is ---  {answer}")
        response_text = answer
        return response_text

    def call_haystack_chatbot(query):
        logging.info("Query passed to haystack chatbot")
        url = "http://localhost:8000/webhooks/rest/webhook"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        request_body = {
            "message": query,
            "sender": "root",
        }
        response = requests.post(url, headers=headers, json=request_body)
        response_text = json.loads(response.text)[0]["text"]
        logging.info("Haystack chatbot answer ----" + response_text)
        return response_text

    def handle_hello(call):

        username = call.data.get("username", DEFAULT_NAME)
        password = call.data.get("password", DEFAULT_NAME)
        tenant_name = call.data.get("tenant_name", DEFAULT_NAME)

        command_classifier = {
            constants.CREATE_SOCIAL_USER: create_social_user,
            constants.ORDER_PIZZA: order_pizza_new,
            constants.GENIE: execute_genie,
        }

        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 1

        recognizer.dynamic_energy_threshold = False
        energy_theshold = 1500
        recognizer.energy_threshold = energy_theshold
        logging.info(energy_theshold)

        hass.states.set("nsl_mic.mic", "activated")
        flag = True
        while hass.states.get("nsl_mic.mic").state == "activated":

            try:
                if flag:
                    day_stage = get_day_stage()
                    convert_text_to_speech(
                        "Good " + day_stage + " " + username + " How may I help you?"
                    )
                    logging.info("Converting text to speech")
                    flag = False
            except Exception as ex:
                logging.info(ex)

            text = record(recognizer).lower()

            try:
                if text.startswith("buddy") or text.startswith("badi"):
                    text = text.replace("buddy", "")
                    text = text.replace("badi", "")
                    if len(text) == 0:
                        response_text = "Please let me know how may I help you?"

                    else:
                        url = "http://127.0.0.1:1234/navigate"
                        data = {
                            "username": username,
                            "password": password,
                            "tenant_name": tenant_name,
                            "command": text,
                        }
                        response = requests.post(url, json=data)
                        response_token = json.loads(response.text)["message"]
                        response_text = command_classifier[response_token](
                            recognizer, username, password, tenant_name, text
                        )
                        if (
                            len(response_text) == 0
                            or response_text.lower().find("virtual assistant") != -1
                            or response_text.lower().find("sorry") != -1
                        ):
                            response_text = call_haystack_chatbot(text)

                elif (
                    text.lower().find("stop buddy") != -1
                    or text.lower().find("stop badi") != -1
                ):
                    hass.states.set("nsl_mic.mic", "sleep")
                    logger.info("NSL Mic stopped")
                    response_text = "NSL Mic stopped"
                else:
                    response_text = """Sorry I cannot understand this command. Please rephrase
                    and start the command with Buddy."""

                convert_text_to_speech(response_text)
                # convert_text_to_speech("Please let me know what")

            except Exception as ex:
                logging.info(ex)

        logging.info("NSL_MIC service ended")

    hass.states.set("nsl_mic.mic", "sleep")
    hass.services.register(DOMAIN, "mic", handle_hello)

    # Return boolean to indicate that initialization was successfully.
    return True
