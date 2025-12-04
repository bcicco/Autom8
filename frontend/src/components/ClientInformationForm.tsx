import React, { useState } from "react";
import ClientInfoStore from "../stores/ClientInfoStore";
import PhaseStore from "../stores/StateStore";

function ClientInformationForm() {
  const [clientData, setClientData] = useState<Record<string, string | number>>(
    {}
  );

  const instantiateClientInfo = React.useCallback(
    ClientInfoStore.getState().instantiateClientInfo,
    []
  );

  const instantiatePhase = React.useCallback(
    PhaseStore.getState().instantiatePhase,
    []
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const text = reader.result as string;

      try {
        const parsed = JSON.parse(text) as Record<string, string | number>;
        setClientData(parsed);
      } catch (err) {
        alert("Invalid JSON file!");
      }
    };
    reader.readAsText(file, "UTF-8");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    instantiateClientInfo(clientData);
    instantiatePhase("confirmClientInfo");
  };

  return (
    <div>
      <h2>Client Information</h2>
      <input type="file" accept=".json" onChange={handleChange} />
      <form onSubmit={handleSubmit}>
        <button type="submit">Save</button>
      </form>
    </div>
  );
}

export default ClientInformationForm;
