import os
import time
import json
import logging
from api import mqtt
from datetime import datetime
from logic import weather
from logic import database
from logic import transaction
from tools.singleton import singleton

DEPLOYMENT_MODE = os.getenv('DEPLOYMENT_MODE', 'TEST')
DISABLE_MQTT    = os.getenv("DISABLE_MQTT", "False").lower() == "true"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOOTER_STATUS_CODES_PATH = os.path.join(BASE_DIR, "resources/scooter-status-codes.json")
STATUS_REDIRECT_PATH = os.path.join(BASE_DIR, "resources/status-codes-redirect.json")

@singleton
class single_ride_service:
    """
    The single_ride_service class handles the logic for unlocking and locking scooters.
    It checks if the user has sufficient funds, if the scooter is available, and if the
    weather is ok. It also performs the necessary database operations to start and end
    the rental as well as communicating with the MQTT broker to unlock and lock the scooter.
    """


    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._db = self.get_db_client()
        self._mqtt = self.get_mqtt_client()
        with open(SCOOTER_STATUS_CODES_PATH, 'r') as f:
            self._status_codes = json.load(f)
        with open(STATUS_REDIRECT_PATH, 'r') as f:
            self._redirect = json.load(f)


    def parse_status(self, code) -> tuple[str, str]:
        status = self._status_codes[str(code)]
        redirect = self._redirect[str(code)]
        return status, redirect

        




    def get_db_client(self) -> object:
        """
        Get the database client for the app.
        The database client is fetched as a singleton instance.
        """
        return database.db()
    


    def get_mqtt_client(self) -> object:
        """
        Get the MQTT client for the app.
        The MQTT client is fetched as a singleton instance.
        """
        return None if DISABLE_MQTT else mqtt.mqtt_client()
    

    def get_rental_info(self, rental_id: int) -> dict:
        """
        Get the rental data from the database.
        
        Args:
            rental_id (int): The ID of the rental to get.
        
        Returns:
            dict: The rental data from the database.

        Example:
        ```python
            rental = self.get_rental_info(rental_id)
            print(rental) -> {
                "rental_id": 4,
                "user_id": 1,
                "scooter_id": 7,
                "active": True,
                "start_time": datetime('2025-03-31 11:25:29'),
                "end_time": time.time(),
                "price": 65.4
            }
        ```
        """
        self._db.ensure_connection()

        _rental = self._db.get_rental_by_id(rental_id)

        if _rental is None:
            self._warn_logger(
                title="get rental info failed",
                culprit="database",
                user_id=rental_id,
                message="rental error: rental not found",
                function=f"get_rental_by_id({rental_id})"
            )
            return None
        else:
            return _rental
    

    def get_user_info(self, user_id: int) -> dict:
        """
        Get the user data from the database.
        
        Args:
            user_id (int): The ID of the user to get.
        
        Returns:
            dict: The user data from the database.

        Example:
        ```python
            user = self.get_user_info(user_id)
            print(user) -> {
                "id": 1, 
                "name": John Doe,
                "funds": 350.0
            }
        ```
        """
        self._db.ensure_connection()

        _user = self._db.get_user(user_id)

        if _user is None:
            self._warn_logger(
                title="get user info failed",
                culprit="database",
                user_id=user_id,
                message="user error: user not found",
                function=f"get_user({user_id})"
            )
            return None
        else:
            return self._parse_user(_user)
    


    def get_scooter_info(self, scooter_id: int) -> dict:
        """
        Get the scooter data from the database.
        
        Args:
            scooter_id (int): The ID of the scooter to get.
        
        Returns:
            dict: The scooter data from the database.

        Example:
        ```python
            scooter = self.get_scooter_into(scooter_id)
            print(scooter) -> {
                "uuid": 1, 
                "latitude": 63.41947, 
                "longtitude": 10.40174, 
                "status": 0
            }
        ```
        """
        self._db.ensure_connection()

        _scooter = self._db.get_scooter(scooter_id)

        if _scooter is None:
            self._warn_logger(
                title="get scooter info failed",
                culprit="database",
                scooter_id=scooter_id,
                message="scooter error: scooter not found",
                function=f"get_scooter({scooter_id})"
            )   
            return None
        else:
            return self._parse_scooter(_scooter)



    def unlock_scooter(self, scooter_id: int, user_id: int) -> tuple[bool, str, str]:
        """
        Unlock a scooter for a user. This function checks if the user has sufficient funds,
        if the scooter is available, and if the weather is ok. It will also perform the
        necessary database operations to start the rental as well as communicating with
        the MQTT broker to unlock the scooter. If all checks pass, the scooter
        is unlocked and the rental is started.
        Args:
            scooter_id (int): The ID of the scooter to unlock.
            user_id (int): The ID of the user unlocking the scooter.
        Returns:
            tuple: 
                * [0]: (bool) True if the unlock was successful, False otherwise.
                * [1]: (str) A message indicating the result of the operation.
        """
        self._db.ensure_connection()

        _scooter = self._db.get_scooter(scooter_id)
        _user = self._db.get_user(user_id)

        if _scooter is None:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="database",
                scooter_id=scooter_id,
                message="scooter error: scooter not found",
                function=f"get_scooter({scooter_id})"
            )   
            return False, "database: scooter not found", "scooter-not-found"
        if _user is None:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="database",
                user_id=user_id,
                message="user error: user not found",
                function=f"get_user({user_id})"
            )
            return False, "database: user not found", "user-not-found"

        user_has_active_rental = self._db.user_has_active_rental(user_id)
        sctr_has_active_rental = self._db.scooter_has_active_rental(scooter_id)

        if user_has_active_rental:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="database",
                user_id=user_id,
                scooter_id=scooter_id,
                message="rental error: user has active rental",
                function=f"user_has_active_rental({user_id})"
            )
            return False, "user has active rental", "user-occupied"
        
        if sctr_has_active_rental:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="database",
                user_id=user_id,
                scooter_id=scooter_id,
                message="rental error: scooter has active rental",
                function=f"scooter_has_active_rental({scooter_id})"
            )
            return False, "scooter is already rented", "scooter-occupied"
        

        self.scooter = self._parse_scooter(_scooter)
        self.user    = self._parse_user(_user)

        if self.scooter["code"] != 0:
            parse_code = self.parse_status(self.scooter["code"])
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="scooter",
                user_id=self.user["id"],
                scooter_id=self.scooter["uuid"],
                message=f"scooter error: {parse_code[0]}",
                function=f"self._db.get_scooter({scooter_id})",
                resp=f"status code: {self.scooter["code"]}",
            )
            return False, parse_code[0], parse_code[1]


        weather_req = weather.is_weather_ok(self.scooter["latitude"], self.scooter["longtitude"])
        balance_req = transaction.validate_funds(self.user, 100.0)


        if not weather_req[0]:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="weather",
                user_id=self.user["id"],
                scooter_id=self.scooter["uuid"],
                message="weather error: weather is not ok",
                function=f"is_weather_ok({self.scooter['latitude']}, {self.scooter['longtitude']})",
                resp=weather_req[1],
                location={"lat": self.scooter["latitude"], "lon": self.scooter["longtitude"]}
            )
            return False, weather_req[1], weather_req[2]
        
        if not balance_req[0]:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="transactions",
                user_id=self.user["id"],
                scooter_id=self.scooter["uuid"],
                message="transaction error: insufficient funds",
                function=f"validate_funds({self.user['id']}, 100.0)",
                resp=balance_req[1],
                transaction={"price": 100.0, "funds": self.user["funds"]}
            )
            return False, balance_req[1], balance_req[2]


        mqtt_unlock = (True, "mqtt disabled", None) if DISABLE_MQTT else self._mqtt.scooter_unlock_single(self.scooter)
        rental_started = self._db.rental_started(self.user["id"], self.scooter["uuid"])
        sctr_status_update = self._db.update_scooter_status(self.scooter["uuid"], self.scooter["status"])

        if not sctr_status_update:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="database",
                scooter_id=self.scooter["uuid"],
                message="database error: scooter status update failed",
                function=f"self._db.update_scooter_status({self.scooter['uuid']}, {self.scooter["status"]})",
            )
            return False, "scooter status update failed", 7

        if mqtt_unlock[0] and rental_started:
            return True, "unlock successful", ""
        elif not mqtt_unlock[0]:
            parsed_status = self.parse_status(mqtt_unlock[1])
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="mqtt",
                user_id=self.user["id"],
                scooter_id=self.scooter["uuid"],
                message="mqtt error: scooter unlock failed",
                function=f"scooter_unlock_single({self.scooter['uuid']})",
                resp=f"satus code: {mqtt_unlock[1]} - {parsed_status[0]}"
            )
            return False, parsed_status[0], parsed_status[1]
        else:
            self._warn_logger(
                title="single scooter unlock failed",
                cuplrit="database",
                scooter_id=self.scooter["uuid"],
                user_id=self.user["id"],
                message="rental error: rental not started",
                function=f"rental_started({self.user['id']}, {self.scooter['uuid']})",
            )
            return False, "database error: rental not started", "rental-error"
        



    def lock_scooter(self, scooter_id: int, user_id: int) -> tuple[bool, str, dict]:
        """
        Lock a scooter for a user. This function checks if the user has an active rental,
        of the given scooter. It will calculate the price of the rental. It will also perform 
        the necessary database operations to end the rental and charge user as well as 
        communicating with the MQTT broker to lock the scooter. If all checks pass, the scooter
        is locked and the rental is ended.
        Args:
            scooter_id (int): The ID of the scooter to lock.
            user_id (int): The ID of the user locking the scooter.
        Returns:
            tuple: 
                * [0]: (bool) True if the lock was successful, False otherwise.
                * [1]: (str) A message indicating the result of the operation.
        """
        self._db.ensure_connection()

        _scooter = self._db.get_scooter(scooter_id)
        _user    = self._db.get_user(user_id)
        _rental  = self._db.get_active_rental_by_user(user_id)

        if _scooter is None:
            self._warn_logger(
                title="single scooter lock failed",
                culprit="database",
                scooter_id=scooter_id,
                message="scooter error: scooter not found",
                function=f"get_scooter({scooter_id})"
            )   
            return False, "database: scooter not found", None
        if _user is None:
            self._warn_logger(
                title="single scooter lock failed",
                culprit="database",
                user_id=user_id,
                message="user error: user not found",
                function=f"get_user({user_id})"
            )
            return False, "database: user not found", None
        if _rental is None:
            self._warn_logger(
                title="single scooter lock failed",
                culprit="database",
                user_id=user_id,
                message="rental error: user has no active rental",
                function=f"get_active_rental_by_user({user_id})"
            )
            return False, "database: rental not found", None
        
        self.scooter = self._parse_scooter(_scooter)
        self.user    = self._parse_user(_user)
        self.rental  = self._parse_rental(_rental)
        time_start = self.rental["start_time"].timestamp()
        time_end   = datetime.fromtimestamp(time.time()).timestamp()
        time_diff  = abs((time_end - time_start) / 60.0)
        mqtt_lock = (True, "mqtt disabled", 0) if DISABLE_MQTT else self._mqtt.scooter_lock_single(self.scooter)
        price = transaction.pay_for_single_ride(self.user, time_diff)
        db_req_payment = self._db.charge_user(self.user["id"], price[2])


        if not price[0]:
            self._warn_logger(
                title="single scooter lock failed",
                culprit="transactions",
                user_id=self.user["id"],
                scooter_id=self.scooter["uuid"],
                message="transaction error: transaction failed",
                function=f"pay_for_single_ride({self.user['id']}, {time_diff})",
                time={"start": time_start, "end": time_end, "diff": time_diff},
                transaction={"price": price[2], "funds": self.user["funds"]},
                resp=mqtt_lock[1]
            )
            return False, price[1], None
        
        if not mqtt_lock[0]:
            self._warn_logger(
                title="single scooter lock failed",
                culprit="mqtt",
                user_id=self.user["id"],
                scooter_id=self.scooter["uuid"],
                message="mqtt error: scooter lock failed",
                function=f"scooter_lock_single({self.scooter['uuid']})",
                resp=mqtt_lock[1]
            )
            return False, mqtt_lock[1], None


        rental_ended = self._db.rental_completed(self.user["id"], price[2], self.scooter["latitude"], self.scooter["longtitude"], mqtt_lock[2])


        if rental_ended and db_req_payment:
            return True, mqtt_lock[1], self.rental
        elif not rental_ended:
            self._warn_logger(
                title="single scooter lock failed",
                culprit="database",
                user_id=self.user["id"],
                scooter_id=self.scooter["uuid"],
                message="rental error: rental not completed",
                function=f"rental_completed({self.user['id']}, {price[2]}, {self.scooter['latitude']}, {self.scooter['longtitude']}, {mqtt_lock[2]})",
            )
            return False, "database error: rental not completed", None
        else:
            self._warn_logger(
                title="single scooter lock failed",
                culprit="database",
                user_id=self.user["id"],
                scooter_id=self.scooter["uuid"],
                message="transaction error: transaction failed",
                function=f"charge_user({self.user['id']}, {price[2]})"
            )
            return False, "database error: transaction failed", None



    def _warn_logger(
            self: object, 
            title: str, 
            culprit: str=None,
            user_id: int=None,
            scooter_id: int=None,
            message: str=None,
            resp: str=None,
            time: dict=None,
            transaction: dict=None,
            function: str=None,
            location: dict=None
    ):
        """
        Log a custom warning message of an incident. Just insert the parameters you want
        to include in the log, and this function will take care of the rest.
        
        Args:
            title (str): The title of the incident.
            culprit (str): Component responsible of the incident.
            user_id (int): ID of the user involved in the incident.
            scooter_id (int): ID of the scooter involved in the incident.
            message (str): A message describing the incident.
            resp (str): The response from the component responsible for the incident.
            time (dict): A dictionary containing the start, end, and time-diff if related to rentals.
            transaction (dict): A dictionary containing the price and funds if related to transactions.
            function (str): The function that caused the incident.
            location (dict): A dictionary containing the latitude and longitude of the scooter.

        Example:
        ```python
            user_id = 1
            scooter_id = 1

            time_start, time_end, time_diff = self._parse_time(self.rental["start_time"])
            transaction_resp = transaction.pay_for_single_ride(self.user, time_diff)

            price = transaction_resp[2]

            self._warn_logger(
                title="single scooter lock failed",
                culprit="transactions",
                user_id=user_id,
                scooter_id=scooter_id,
                message="transaction error: transaction failed",
                resp=transaction_resp[1],
                time={"start": time_start, "end": time_end, "diff": time_diff},
                transaction={"price": price, "funds": self.user["funds"]},
                function=f"pay_for_single_ride({self.user}, {time_diff})",
                location={"lat": self.scooter["latitude"], "lon": self.scooter["longtitude"]}
            )
        ```
        """
        if culprit is not None:
            self._logger.warning(f"{title} - {culprit}")
        elif title is not None:
            self._logger.warning(title)
        else:
            self._logger.warning("unknown error")


        if user_id is not None:
            self._logger.warning(f"\tuser-id: \t{user_id}")
        if scooter_id is not None:
            self._logger.warning(f"\tscooter-id: \t{scooter_id}")
        if resp is not None:
            self._logger.warning(f"\tresponse: \t{resp}")
        if time is not None:
            start_time_tmp = datetime.fromtimestamp(time["start"])
            end_time_tmp   = datetime.fromtimestamp(time["end"])
            self._logger.warning(f"\ttime:")
            self._logger.warning(f"\t\tstart: {time['start']} \t {start_time_tmp}")
            self._logger.warning(f"\t\tend: {time['end']} \t {end_time_tmp}")
            self._logger.warning(f"\t\tdiff: {time['diff']}")
        if transaction is not None:
            self._logger.warning(f"\tprice: \t{transaction['price']}")
            self._logger.warning(f"\tuser-funds: \t{transaction['funds']}")
        if message is not None:
            self._logger.warning(f"\tmessage: \t{message}")
        if function is not None:
            self._logger.warning(f"\tfunction: \t{function}")
        if location is not None:
            self._logger.warning(f"\tlocation:")
            self._logger.warning(f"\t\tlatitude: {location['lat']}")
            self._logger.warning(f"\t\tlongtitude: {location['lon']}")

    

    def _parse_scooter(self, scooter: dict) -> dict:
        """
        Parse the scooter data from the database.
        
        Args:
            scooter (dict): The scooter data from the database.
        
        Returns:
            dict: The parsed scooter data.

        Example:
        ```python
            _scooter = self._db.get_scooter(scooter_id)
            self._parse_scooter(_scooter) -> {
                "uuid": 1, 
                "latitude": 63.41947, 
                "longtitude": 10.40174, 
                "status": 0
            }
        ```
        """
        return {
            "uuid": scooter[0],
            "latitude": scooter[1],
            "longtitude": scooter[2],
            "status": scooter[3]
        }
    


    def _parse_user(self, user: dict) -> dict:
        """
        Parse the user data from the database.
        
        Args:
            user (dict): The user data from the database.
        
        Returns:
            dict: The parsed user data.

        Example:
        ```python
            _user = self._db.get_user(user_id)
            self._parse_user(_user) -> {
                "id": 1, 
                "name": John Doe,
                "funds": 350.0
            }
        ```
        """
        return {
            "id": user[0],
            "name": user[1],
            "funds": user[2]
        }
    


    def _parse_rental(self, rental: dict) -> dict:
        """
        Parse the rental data from the database.
        
        Args:
            rental (dict): The rental data from the database.
        
        Returns:
            dict: The parsed rental data.

        Example:
        ```python
            _rental  = self._db.get_active_rental_by_user(user_id)
            self._parse_rental(_rental) -> {
                "rental_id": 4,
                "user_id": 1,
                "scooter_id": 7,
                "active": True,
                "start_time": datetime('2025-03-31 11:25:29'),
                "end_time": time.time(),
                "price": 65.4
            }
        ```
        """
        return {
            "rental_id": rental[0],
            "user_id": rental[1],
            "scooter_id": rental[2],
            "active": rental[3],
            "start_time": rental[4],
            "end_time": time.time(),
            "price": rental[6]
        }
    


    def _parse_time(self, time_start) -> tuple[float, float, float]:
        """
        Parse the time data from the database.
        
        Args:
            time_start (float): The start time of the rental.
        
        Returns:
            tuple:
                * time_start (float): The start time of the rental in UTC seconds.
                * time_end (float): The end time of the rental in UTC seconds.
                * time_diff (float): The difference between the start and end time in minutes.
        """
        time_start = time_start.timestamp()
        time_end   = datetime.fromtimestamp(time.time()).timestamp()
        time_diff  = abs((time_end - time_start) / 60.0)
        return (time_start, time_end, time_diff)