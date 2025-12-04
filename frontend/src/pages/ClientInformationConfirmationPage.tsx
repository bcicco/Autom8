import React from "react";
import ClientInfoStore from "../stores/ClientInfoStore";
import ClearClientButton from "../components/ClearClientButton";
import LogOutButton from "../components/LogOutButton";
import { useShallow } from "zustand/shallow";
import ConfirmClientButton from "../components/ConfirmClientButton";
import ColorBends from "../components/ColorBends";
function ClientInformationConfirmationPage({ name }: { name: string }) {
  const clientInfo = React.useMemo(
    () => ClientInfoStore(useShallow((state) => state.clientInfo)),
    []
  );
  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      {/* Fullscreen background */}
      <div style={{ position: "absolute", inset: 0, zIndex: 0 }}>
        <ColorBends
          colors={["#FFAD00", "#C724B1", "#4D4DFF"]}
          rotation={45}
          speed={0.8}
          scale={1}
          frequency={1.5}
          warpStrength={1.2}
          mouseInfluence={0.8}
          parallax={1}
          noise={0.1}
        />
      </div>
      <div
        className="vertical-center"
        style={{ position: "relative", zIndex: 10 }}
      >
        <h2>Client Information submitted by {name}:</h2>
        <pre>{JSON.stringify(clientInfo, null, 2)}</pre>
        <ClearClientButton />
        <LogOutButton />
        <ConfirmClientButton />
      </div>
    </div>
  );
}

export default ClientInformationConfirmationPage;
