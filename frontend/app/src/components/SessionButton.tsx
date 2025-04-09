import Button from "@mui/material/Button";

type SessionButtonProps = {
  handleButton: () => void;
  type?: string;
};

export function SessionButton({ handleButton, type }: SessionButtonProps) {
  const getButtonText = () => {
    switch (type) {
      case "start":
        return "Start Session";
      case "end":
        return "End Session";
      case "join":
        return "Join Session";
      case "back":
        return "Back";
    }
  };

  return (
    <div className="button-container">
      <Button
        variant="contained"
        color="secondary"
        onClick={handleButton}
        style={{ width: "90vw", height: "7vh", fontSize: "1.5rem" }}
        className="button-t"
      >
        {getButtonText()}
      </Button>
    </div>
  );
}
