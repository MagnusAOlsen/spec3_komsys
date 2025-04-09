import { SessionButton } from "../components/SessionButton";
import { Image } from "../components/Image";
import multi_session from "../assets/img/multi_session.png";
import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";

const SessionPage = () => {
  const navigate = useNavigate();
  const { scooter_id } = useParams<{ scooter_id: string }>();
  const [userId, setUserId] = useState<string>("");
  const [mid, setMid] = useState<string>("");

  const scooter_id_num = parseInt(scooter_id || "0", 10);
  const apiUrl =
    import.meta.env.VITE_API_URL || "http://localhost:8080/api/v1/";

  useEffect(() => {
    if (userId === "") {
      const storedId = sessionStorage.getItem("user_id");
      if (storedId) {
        setUserId(storedId);
      }
      return;
    }
  });

  useEffect(() => {
    //usikker på om den egt er lagret i sessionStorage slik som userId?
    if (mid === "") {
      const storedMid = sessionStorage.getItem("mid");
      if (storedMid) {
        setMid(storedMid);
      }
      return;
    }
  });

  const handleJoinSession = async () => {
    const resp = await fetch(
      `${apiUrl}scooter/${scooter_id_num}/join-session/?${mid}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    const data = await resp.json();

    if (resp.status === 200) {
      if (data.redirect === "join-session") {
        navigate(`/join-session/${data.id}`);
      } else if (data.redirect === "session-page") {
        navigate(`/session-page/${data.id}`);
      }
    } else {
      console.error("Lock failed: " + data.message);
      alert("Lock failed");
    }
  };

  return (
    <div className="error-page">
      <h1 className="page-title">Session </h1>
      <Image src={multi_session} />
      <p className="primary-paragraph">
        Start the session when everyone has joined.
      </p>
      <SessionButton handleButton={handleJoinSession} type="start" />
    </div>
  );
};

export default SessionPage;
