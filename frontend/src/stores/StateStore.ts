import { create } from "zustand";

type PhaseState = {
  phase: string;
  instantiatePhase: (phase: string) => void;
};

const PhaseStore = create<PhaseState>((set) => ({
  phase: "login",
  instantiatePhase: (phase: string) => set({ phase: phase }),
}));

export default PhaseStore;
