import React from "react";
import UserStore from "../stores/UserStore";
import phaseStore from "../stores/StateStore";

function LoginForm() {
  try {
    const [loginDetails, setLoginDetails] = React.useState<{
      username: string;
      password: string;
    }>({
      username: "",
      password: "",
    });
    console.log("useState called successfully");

    const instantiateUser = React.useCallback(
      UserStore.getState().instantiateUser,
      []
    );

    const instantiatePhase = React.useCallback(
      phaseStore.getState().instantiatePhase,
      []
    );
    console.log("Zustand selector called successfully");

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
      console.log("handleChange called for:", e.target.name);
      const name = e.target.name;
      const value = e.target.value;
      setLoginDetails((prevDetails) => ({
        ...prevDetails,
        [name]: value,
      }));
    };

    const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
      e.preventDefault();
      console.log("attempting to login....");
      console.log("login successul!");
      instantiateUser(loginDetails.username, 1);
      instantiatePhase("uploadClientInfo");
    };

    console.log("LoginForm rendering - about to return JSX");

    return (
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="username">Username:</label>
          <input name="username" type="text" onChange={handleChange} />
          <label htmlFor="password">Password:</label>
          <input name="password" type="password" onChange={handleChange} />
          <button type="submit">Login</button>
        </div>
      </form>
    );
  } catch (error) {
    console.error("Error in LoginForm:", error);
    throw error;
  }
}
export default LoginForm;
