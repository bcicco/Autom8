import { useState, useEffect, useRef } from "react";
import React from "react";
import UserStore from "../stores/UserStore";

interface UserInputRequest {
  field_name: string;
  prompt: string;
  input_type: "text" | "code" | "choice" | "confirmation";
  options?: string[];
}

const LaunchAgentForm = () => {
  const [screenshot, setScreenshot] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [userInputRequest, setUserInputRequest] =
    useState<UserInputRequest | null>(null);
  const [userInputValue, setUserInputValue] = useState<string>("");
  const user = React.useMemo(() => UserStore.getState().user, []);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket(`ws://localhost:8000/ws/${user.id}`);

    ws.current.onopen = () => {
      console.log("WebSocket connected");
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "screenshot") {
        setScreenshot(`data:image/png;base64,${data.data}`);
        setStatus(data.message);
      } else if (data.type === "error") {
        setStatus(`Error: ${data.message}`);
      } else if (data.type === "user_input_request") {
        console.log("User input requested:", data.data);
        setUserInputRequest(data.data);
        setUserInputValue("");
      }
    };

    ws.current.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.current.onclose = () => {
      console.log("WebSocket disconnected");
    };

    return () => {
      ws.current?.close();
    };
  }, [user.id]);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const url = formData.get("url") as string;

    fetch(`${import.meta.env.VITE_API_URL}/trigger`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url, user_id: String(user.id) }),
    });
  }

  function handleUserInputSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (ws.current && userInputRequest) {
      ws.current.send(
        JSON.stringify({
          type: "user_input_response",
          value: userInputValue,
        })
      );

      setUserInputRequest(null);
      setUserInputValue("");
      setStatus("Input submitted, continuing automation...");
    }
  }

  function handleChoiceSelection(choice: string) {
    if (ws.current && userInputRequest) {
      ws.current.send(
        JSON.stringify({
          type: "user_input_response",
          value: choice,
        })
      );

      setUserInputRequest(null);
      setStatus("Choice submitted, continuing automation...");
    }
  }

  return (
    <div>
      <div>
        <form onSubmit={handleSubmit}>
          <label>URL</label>
          <input
            type="text"
            name="url"
            defaultValue="https://fill.dev/form/login-simple"
          />
          <button type="submit">Launch Agent</button>
        </form>

        {status && <p>Status: {status}</p>}

        {userInputRequest && (
          <div>
            <h3>Input Required</h3>
            <p>{userInputRequest.prompt}</p>

            {userInputRequest.input_type === "choice" &&
            userInputRequest.options ? (
              <div>
                {userInputRequest.options.map((option) => (
                  <button
                    key={option}
                    onClick={() => handleChoiceSelection(option)}
                  >
                    {option}
                  </button>
                ))}
              </div>
            ) : (
              <form onSubmit={handleUserInputSubmit}>
                <input
                  type="text"
                  value={userInputValue}
                  onChange={(e) => setUserInputValue(e.target.value)}
                  placeholder={
                    userInputRequest.input_type === "code"
                      ? "Enter verification code"
                      : "Enter value"
                  }
                  autoFocus
                />
                <button type="submit" disabled={!userInputValue.trim()}>
                  Submit
                </button>
              </form>
            )}
          </div>
        )}
      </div>

      {screenshot && (
        <div>
          <h3>Live Browser View:</h3>
          <img
            src={screenshot}
            alt="Browser screenshot"
            style={{ maxWidth: "60%", height: "auto" }}
          />
        </div>
      )}
    </div>
  );
};

export default LaunchAgentForm;
