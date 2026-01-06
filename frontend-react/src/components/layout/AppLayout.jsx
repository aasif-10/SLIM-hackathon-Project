import React from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { PageTransition } from "../animations/PageTransition";
import "./layout.css";

export const AppLayout = ({ children, title }) => {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-content">
        <TopBar title={title} />
        <div className="scroll-area">
          <main className="container">
            <PageTransition>{children}</PageTransition>
          </main>
        </div>
      </div>
    </div>
  );
};
