import { Routes, Route } from "react-router-dom";
import RentScooter from "./pages/RentScooter";
import ActiveRental from "./pages/ActiveRental";
import InactiveRental from "./pages/InactiveRental";
import ErrorPage from "./pages/ErrorPage";
import SessionPage from "./pages/SessionPage";
import ActiveSession from "./pages/ActiveSession";
import JoinSession from "./pages/JoinSession";

function App() {
  return (
    <Routes>
      <Route path="/scooter/:scooter_id" element={<RentScooter />} />
      <Route path="/scooter/:scooter_id/active" element={<ActiveRental />} />
      <Route
        path="/scooter/:scooter_id/inactive"
        element={<InactiveRental />}
      />
      <Route path="/error/:error_type" element={<ErrorPage />} />
      <Route path="/session-page" element={<SessionPage />} />
      <Route
        path="/active_mutli_session/:session_id"
        element={<ActiveSession />}
      />
      <Route path="/join_session" element={<JoinSession />} />
    </Routes>
  );
}

export default App;
