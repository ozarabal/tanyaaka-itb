interface ElephantIconProps {
  className?: string;
}

export default function ElephantIcon({ className = "w-5 h-5" }: ElephantIconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M19.5 3C17.57 3 15.79 3.75 14.46 5.04C13.36 4.38 12.06 4 10.7 4C6.7 4 3.44 7.26 3.44 11.26C3.44 11.94 3.54 12.6 3.72 13.22C2.68 14.14 2 15.48 2 17C2 17.55 2.45 18 3 18H4.5C4.5 19.1 5.4 20 6.5 20C7.6 20 8.5 19.1 8.5 18H13C13 19.1 13.9 20 15 20C16.1 20 17 19.1 17 18H17.5C17.5 18 19 18 20 16.5C21.38 14.38 22 12 22 9.5C22 5.91 21.09 3 19.5 3ZM7.5 14C6.67 14 6 13.33 6 12.5C6 11.67 6.67 11 7.5 11C8.33 11 9 11.67 9 12.5C9 13.33 8.33 14 7.5 14Z" />
    </svg>
  );
}
