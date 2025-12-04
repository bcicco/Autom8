import { create } from "zustand";

type User = {
  username: string;
  id: number;
};

type UserState = {
  user: User;
  instantiateUser: (username: string, id: number) => void;
  logOutUser: () => void;
};

const UserStore = create<UserState>((set) => ({
  user: { username: "loggedout", id: -1 },
  instantiateUser: (username: string, id: number) =>
    set({ user: { username: username, id: id } }),
  logOutUser() {
    set({ user: { username: "loggedout", id: -1 } });
  },
}));

export default UserStore;
