import React from "react";
import { motion } from "framer-motion";
import clsx from "clsx";
import "./ui.css";

// --- BUTTON ---
export const Button = ({
  children,
  variant = "primary",
  size = "md",
  className,
  ...props
}) => {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      whileHover={{ scale: 1.02 }}
      className={clsx("btn", `btn-${variant}`, `btn-${size}`, className)}
      {...props}
    >
      {children}
    </motion.button>
  );
};

// --- CARD ---
export const Card = ({ children, className, ...props }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={clsx("card", className)}
      {...props}
    >
      {children}
    </motion.div>
  );
};

// --- INPUT ---
export const Input = ({ label, error, className, ...props }) => {
  return (
    <div className="form-group">
      {label && <label className="label">{label}</label>}
      <input
        className={clsx("input", error && "input-error", className)}
        {...props}
      />
      {error && <span className="input-error-msg">{error}</span>}
    </div>
  );
};

// --- BADGE ---
export const Badge = ({ children, variant = "neutral", className }) => {
  return (
    <span className={clsx("badge", `badge-${variant}`, className)}>
      {children}
    </span>
  );
};
