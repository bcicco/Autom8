import { create } from "zustand";

type User = {
  username: string | null;
  id: number | null;
};

type UserState = {
  user: User;
  instantiateUser: (username: string, id: number) => void;
  logOutUser: () => void;
};

const UserStore = create<UserState>((set) => ({
  user: { username: null, id: null },
  instantiateUser: (username: string, id: number) =>
    set({ user: { username: username, id: id } }),
  logOutUser() {
    set({ user: { username: null, id: null } });
  },
}));

export default UserStore;
