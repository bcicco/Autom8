import UserStore from "../stores/UserStore";
import React from "react";
import phaseStore from "../stores/StateStore";

function LogOutButton() {
  const instantiatePhase = React.useCallback(
    phaseStore.getState().instantiatePhase,
    []
  );

  const logOutUser = React.useCallback(UserStore.getState().logOutUser, []);

  function handleOnclick() {
    logOutUser();
    instantiatePhase("login");
  }

  return <button onClick={handleOnclick}>Log Out</button>;
}
export default LogOutButton;
