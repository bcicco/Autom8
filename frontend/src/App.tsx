import "./App.css";

import LoginPage from "./pages/LoginPage";
import UploadClientInfoPage from "./pages/UploadClientInfoPage";
import ClientInformationConfirmationPage from "./pages/ClientInformationConfirmationPage";
import AgentPage from "./pages/AgentPage";
import PhaseStore from "./stores/StateStore";
import { useShallow } from "zustand/shallow";
import UserStore from "./stores/UserStore";
import React from "react";
function App() {
  const phase = PhaseStore(useShallow((state) => state.phase));

  if (phase === "login") {
    return <LoginPage />;
  } else if (phase === "uploadClientInfo") {
    return <UploadClientInfoPage />;
  } else if (phase === "confirmClientInfo") {
    return <ClientInformationConfirmationPage />;
  } else if (phase === "URLDetails") {
    return <AgentPage />;
  } else {
    return <div>Unknown Phase</div>;
  }
}

export default App;
