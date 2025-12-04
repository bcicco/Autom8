import ClientInfoStore from "../stores/ClientInfoStore";
import React from "react";
import PhaseStore from "../stores/StateStore";

function ClearClientButton() {
  const clearClientInfo = React.useCallback(
    ClientInfoStore.getState().clearClientInfo,
    []
  );

  const instantiatePhase = React.useCallback(
    PhaseStore.getState().instantiatePhase,
    []
  );

  function handleClear() {
    clearClientInfo();
    instantiatePhase("uploadClientInfo");
  }
  return <button onClick={handleClear}>ClearClient</button>;
}
export default ClearClientButton;
