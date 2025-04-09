import { SessionButton } from "../components/SessionButton";
import { Image } from "../components/Image";
import scooter from "../assets/img/scooter.gif";
import { useNavigate, useParams } from "react-router-dom";

const ActiveSession = () => {
  const navigate = useNavigate();
  const { scooter_id } = useParams<{ scooter_id: string }>();
  const scooter_id_num = parseInt(scooter_id || "0", 10);

  const handleButton = () => {
    navigate(`/scooter/${scooter_id_num}/inactive`);
  };
  return (
    <div>
      <h1 className="page-title">Session Started</h1>
      <Image src={scooter} />
      <SessionButton handleButton={handleButton} type="end" />
    </div>
  );
};

export default ActiveSession;
