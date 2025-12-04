import { useState, useEffect, useRef } from "react";
import React from "react";
import UserStore from "../stores/UserStore";

const LaunchAgentForm = () => {
  const [screenshot, setScreenshot] = useState<string>("");
  const [status, setStatus] = useState<string>("");
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

  return (
    <div>
      <form onSubmit={handleSubmit} style={{ flexDirection: "column" }}>
        <label>URL</label>
        <input
          type="text"
          name="url"
          defaultValue="https://fill.dev/form/login-simple"
        />
        <button type="submit">Launch Agent</button>
      </form>

      {status && <p>Status: {status}</p>}

      {screenshot && (
        <div>
          <h3>Live Browser View:</h3>
          <img
            src={screenshot}
            alt="Browser screenshot"
            style={{
              width: "100%",
              maxWidth: "800px",
              border: "1px solid #ccc",
            }}
          />
        </div>
      )}
    </div>
  );
};

export default LaunchAgentForm;
