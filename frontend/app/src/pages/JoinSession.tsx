import { useEffect, useState } from "react";
import { SessionButton } from "../components/SessionButton";
import { Image } from "../components/Image";
import multi_session from "../assets/img/multi_session.png";
import { useNavigate, useParams } from "react-router-dom";

const JoinSession = () => {
  const [userName, setUserName] = useState<string>("");
  const [userId, setUserId] = useState<string>("");
  const [mid, setMid] = useState<string>("");
  const navigate = useNavigate();
  const { scooter_id } = useParams<{ scooter_id: string }>();
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

    const controller = new AbortController();
    fetch(`${apiUrl}user/${userId}`, { signal: controller.signal })
      .then((response) => response.json())
      .then((res) => {
        if (res.message?.name) {
          setUserName(res.message.name.split(" ")[0]);
        }
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          console.error("Error:", error);
        }
      });

    return () => controller.abort();
  }, [userId]);

  const handleButtonBack = () => {
    navigate(`/scooter/${scooter_id_num}`);
  };

  const handleButtonJoin = async () => {
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
      <h1 className="page-title">{userName}'s session</h1>
      <Image src={multi_session} />
      <SessionButton handleButton={handleButtonJoin} type="join" />
      <SessionButton handleButton={handleButtonBack} type="back" />
    </div>
  );
};

export default JoinSession;
