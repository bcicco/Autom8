import { create } from "zustand";

type ClientInfo = Record<string, string | number>;

type ClientInfoState = {
  clientInfo: ClientInfo | null;
  instantiateClientInfo: (clientInfo: ClientInfo) => void;
  clearClientInfo: () => void;
};

const ClientInfoStore = create<ClientInfoState>((set) => ({
  clientInfo: null,
  instantiateClientInfo: (clientInfo: ClientInfo) =>
    set({ clientInfo: clientInfo }),
  clearClientInfo() {
    set({ clientInfo: null });
  },
}));

export default ClientInfoStore;
