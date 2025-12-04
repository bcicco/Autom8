import LogOutButton from "../components/LogOutButton";
import UserStore from "../stores/UserStore";
import ClientInformationForm from "../components/ClientInformationForm";
import React from "react";
import ColorBends from "../components/ColorBends";
function UploadClientInfoPage() {
  const user = React.useMemo(() => UserStore.getState().user, []);

  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      {/* Fullscreen background */}
      <div style={{ position: "absolute", inset: 0, zIndex: 0 }}>
        <ColorBends
          colors={["#ff5c7a", "#8a5cff", "#00ffd1"]}
          rotation={0}
          speed={0.8}
          scale={0.8}
          frequency={1.5}
          warpStrength={1.2}
          mouseInfluence={0.8}
          parallax={0.6}
          noise={0.08}
        />
      </div>
      <div
        className="vertical-center"
        style={{ position: "relative", zIndex: 10 }}
      >
        <h1>Welcome, {user.username}!</h1>
        <p> Please upload your client information:</p>
        <ClientInformationForm />
        <LogOutButton />
      </div>
    </div>
  );
}
export default UploadClientInfoPage;
