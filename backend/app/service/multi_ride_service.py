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
class multi_ride_service:


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







def session_request(self, user_id, scooter_id):

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
            return False, "database: scooter not found", "scooter-not-found", -1
        if _user is None:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="database",
                user_id=user_id,
                message="user error: user not found",
                function=f"get_user({user_id})"
            )
            return False, "database: user not found", "user-not-found", -1

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
            return False, "user has active rental", "user-occupied", -1
        
        if sctr_has_active_rental:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="database",
                user_id=user_id,
                scooter_id=scooter_id,
                message="rental error: scooter has active rental",
                function=f"scooter_has_active_rental({scooter_id})"
            )
            return False, "scooter is already rented", "scooter-occupied", -1

        self.scooter = self._parse_scooter(_scooter)
        self.user    = self._parse_user(_user)


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
            return False, weather_req[1], weather_req[2], -1
        
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
            return False, balance_req[1], balance_req[2], -1

        _multisession = self._db.getMultisession(self.scooter[1], self.scooter[2])


        if _multisession == None:
            _multisession = self._db.createMultisession(self.user['id'], self.scooter['latitude'], self.scooter['logtitude'])
            if _multisession[0] is not False:
                _corider = self._db.addParticipant(self.user['id'], self.scooter['uuid'], _multisession[1])
                return True, "", "session-page", self.multisession['id']
            else:
                return False, "", "session-error", -1
        else:
            self.multisession = self._parse_multisession(_multisession)
            # _corider = self._db.addParticipant(self.user['id'], self.scooter['uuid'], _multisession[1])
            return True, "", "join-session", self.multisession['id']




def join_session(self, session_id, user_id, scooter_id):

        self._db.ensure_connection()

        _scooter = self._db.get_scooter(scooter_id)
        _user = self._db.get_user(user_id)
        _session = self._db.get_session(session_id)

        if _scooter is None:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="database",
                scooter_id=scooter_id,
                message="scooter error: scooter not found",
                function=f"get_scooter({scooter_id})"
            )   
            return False, "database: scooter not found", "scooter-not-found", -1
        if _user is None:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="database",
                user_id=user_id,
                message="user error: user not found",
                function=f"get_user({user_id})"
            )
            return False, "database: user not found", "user-not-found", -1
        
        if _session is None:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="database",
                user_id=user_id,
                message="session error: session not found",
                function=f"get_session({user_id})"
            )
            return False, "database: user not found", "user-not-found", -1

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
            return False, "user has active rental", "user-occupied", -1
        
        if sctr_has_active_rental:
            self._warn_logger(
                title="single scooter unlock failed",
                culprit="database",
                user_id=user_id,
                scooter_id=scooter_id,
                message="rental error: scooter has active rental",
                function=f"scooter_has_active_rental({scooter_id})"
            )
            return False, "scooter is already rented", "scooter-occupied", -1

        self.scooter = self._parse_scooter(_scooter)
        self.user    = self._parse_user(_user)
        self.session = self._parse_session(_session)


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
            return False, weather_req[1], weather_req[2], -1
        
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
            return False, balance_req[1], balance_req[2], -1

        mqtt_unlock = (True, "mqtt disabled", None) if DISABLE_MQTT else self._mqtt.scooter_unlock_single(self.scooter)
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

        if mqtt_unlock[0]:
            session_joined = self._db.addParticipant(self.user['id'], self.scooter['uuid'], self.session['id'])
            if session_joined[0]:
                return True, "session joined", "await-session", -1
            else:
                return False, "error joining sesssion", "scooter", self.scooter['uuid']
        else:
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
            return False, parsed_status[0], parsed_status[1], -1





def start_session(self, session_id, user_id, scooter_id):

    self._db.ensure_connection()

    _user = self._db.get_user(user_id)

    if _user is None:
        self._warn_logger(
            title="single scooter unlock failed",
            culprit="database",
            user_id=user_id,
            message="user error: user not found",
            function=f"get_user({user_id})"
        )
        return False, "database: user not found", "user-not-found", -1

    self.user    = self._parse_user(_user)

    session_started = self._db.start_session(session_id, user_id)

    if session_started:
        return True, "session started", "active-multi-session", session_id
    else:
        return False, "session not started", "scooter", scooter_id


def await_start(self, session_id):

    started = False

    while not started:
        started = self._db.is_session_active(session_id)

    return True, "session started", "active"







def end_session(self, session_id, user_id, scooter_id):
    self._db.ensure_connection()

    _scooter = self._db.get_scooter(scooter_id)
    _user = self._db.get_user(user_id)
    _session = self._db.get_session(session_id)

    if _scooter is None:
        self._warn_logger(
            title="single scooter unlock failed",
            culprit="database",
            scooter_id=scooter_id,
            message="scooter error: scooter not found",
            function=f"get_scooter({scooter_id})"
        )   
        return False, "database: scooter not found", "scooter-not-found", -1
    if _user is None:
        self._warn_logger(
            title="single scooter unlock failed",
            culprit="database",
            user_id=user_id,
            message="user error: user not found",
            function=f"get_user({user_id})"
        )
        return False, "database: user not found", "user-not-found", -1

    # TODO: Legg til sjekk for _session is None



    self.scooter = self._parse_scooter(_scooter)
    self.user    = self._parse_user(_user)
    self.session = self._parse_session(_session)

    time_start = self.rental["start_time"].timestamp()
    time_end   = datetime.fromtimestamp(time.time()).timestamp()
    time_diff  = abs((time_end - time_start) / 60.0)

    coriders = self._db.get_coriders(session_id) # dette er en int

    balance_calc = transaction.calculate_discount(coriders.length, time_diff)
    balance_req  = transaction.pay_for_multi_ride(balance_calc, coriders)
    
    session_ended = self._db.session_ended(user_id, session_id, self.scooter["latitude"], self.scooter["longtitude"])

    if not session_ended:
        return False, "session not ended", "scooter"

    coriders_filtered = []

    for rider in coriders:
        has_ended = self._db.has_active_rental(rider['id'], self.session['start_time'])
        if not has_ended:
            coriders_filtered.append(rider)


    db_req_payment = self._db.charge_users(session_id, balance_req, coriders_filtered)
        
    if not db_req_payment[0]:
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
        return False, balance_req[1], balance_req[2], -1

    return True, "session ended", "inactive"
    

    

    

    # TODO: Legg til parse-funksjoner
    # TODO: Lag database-funksjoner
    # TODO: Lag tranasction-funksjoner
    # TODO: Implementer MQTT lock
    # TODO: Legg inn loggere
    # TODO: Legg inn manglende sider i front-end: join-session, session-error, session-page, await-session
    