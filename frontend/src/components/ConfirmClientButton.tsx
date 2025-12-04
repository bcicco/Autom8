import PhaseStore from "../stores/StateStore";
import React from "react";
function ConfirmClientButton() {
  const instantiatePhase = React.useCallback(
    PhaseStore.getState().instantiatePhase,
    []
  );

  const handleConfirm = () => {
    instantiatePhase("URLDetails");
  };
  return <button onClick={handleConfirm}>Confirm</button>;
}
export default ConfirmClientButton;
