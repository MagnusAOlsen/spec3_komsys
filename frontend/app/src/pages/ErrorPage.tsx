import { useState, useEffect } from "react";
import low_battery from "../assets/img/low_battery.png";
import bad_weather from "../assets/img/bad_weather.png";
import insufficient_funds from "../assets/img/insufficient_funds.png";
import error from "../assets/img/error.png";
import { Image } from "../components/Image";
import { useParams } from "react-router-dom";

const ErrorPage = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorImage, setErrorImage] = useState<string | null>(null);
  const [errorTitle, setErrorTitle] = useState<string | null>(null);
  const { error_type } = useParams<{ error_type: string }>();
  const [errorType, setErrorType] = useState<string | undefined>("low-battery");

  const ErrorDict: Record<
    string,
    { title: string; message: string; image: string }
  > = {
    "low-battery": {
      title: "Low Battery",
      message:
        "The e-scooter has a low battery. Please change to another e-scooter.",
      image: low_battery,
    },
    "bad-weather": {
      title: "Bad Weather",
      message:
        "The weather is not suitable for driving. Please try again later.",
      image: bad_weather,
    },
    "insufficient-funds": {
      title: "Insufficient Funds",
      message: "You do not have enough funds to rent this e-scooter.",
      image: insufficient_funds,
    },
    "rental-error": {
      title: "Rental Error",
      message:
        "There was an error while renting the e-scooter. Please try again.",
      image: low_battery,
    },
    "user-occupied": {
      title: "User Occupied",
      message:
        "You are already renting an e-scooter. Please return it before renting another one.",
      image: error,
    },
    "scooter-occupied": {
      title: "Scooter Occupied",
      message:
        "The e-scooter is currently occupied. Please try another e-scooter.",
      image: error,
    },
    "scooter-inoperable": {
      title: "Scooter Inoperable",
      message: "The e-scooter is inoperable. Please try another e-scooter.",
      image: error,
    },
    "user-not-found": {
      title: "User not Found",
      message: "The user was not found. Please try again.",
      image: error,
    },
    "scooter-not-found": {
      title: "Scooter not Found",
      message: "The e-scooter was not found. Please try again.",
      image: error,
    },
    "transaction-error": {
      title: "Transaction Error",
      message: "There was an error with the transaction. Please try again.",
      image: error,
    },
    "session-error": {
      title: "Session Error",
      message: "An session error occurred. Please try again.",
      image: error,
    },
  };

  const setError = (type: string | undefined) => {
    if (type !== undefined) {
      if (ErrorDict[type]) {
        setErrorMessage(ErrorDict[type].message);
        setErrorImage(ErrorDict[type].image);
        setErrorTitle(ErrorDict[type].title);
      } else {
        setErrorMessage("An unknown error occurred. Please try again.");
        setErrorImage(error);
        setErrorTitle("Unknown Error");
      }
    }
  };

  useEffect(() => {
    setErrorType(error_type?.toString());
    setError(error_type?.toString());
  });

  return (
    <div className="error-page">
      <h1 className="page-title">{errorTitle || "Unknown Error"}</h1>
      {errorImage && <Image src={errorImage} width="19rem" height="10rem" />}
      <p className="primary-paragraph">{errorMessage}</p>
    </div>
  );
};

export default ErrorPage;
