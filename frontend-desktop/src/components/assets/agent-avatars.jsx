import React from 'react';

export const AgentAvatars = {
  planner: (color) => (
    <svg className="w-8 h-8 animate-pulse" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="50" cy="50" r="40" stroke={color} strokeWidth="6" strokeDasharray="10 5" />
      <circle cx="50" cy="50" r="20" fill={color} />
    </svg>
  ),
  coder: (color) => (
    <svg className="w-8 h-8 animate-spin [animation-duration:8s]" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="20" y="20" width="60" height="60" rx="10" stroke={color} strokeWidth="6" />
      <path d="M40 45L30 50L40 55M60 45L70 50L60 55" stroke={color} strokeWidth="6" strokeLinecap="round" />
    </svg>
  ),
  researcher: (color) => (
    <svg className="w-8 h-8" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="50" cy="40" r="25" stroke={color} strokeWidth="6" />
      <path d="M70 70L90 90" stroke={color} strokeWidth="6" strokeLinecap="round" />
    </svg>
  ),
  browser: (color) => (
    <svg className="w-8 h-8" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="50" cy="50" r="40" stroke={color} strokeWidth="6" />
      <path d="M10 50H90M50 10C65 25 65 75 50 90" stroke={color} strokeWidth="6" />
    </svg>
  ),
  validator: (color) => (
    <svg className="w-8 h-8" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="50,10 90,85 10,85" stroke={color} strokeWidth="6" fill="none" />
      <path d="M40 55L48 63L65 42" stroke={color} strokeWidth="6" strokeLinecap="round" />
    </svg>
  )
};
