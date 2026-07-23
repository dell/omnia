import Button from '../../../components/Button';

interface AddTargetSectionProps {
  newTargetName: string;
  onNameChange: (name: string) => void;
  onAdd: () => void;
  error: string;
}

export const AddTargetSection = ({ newTargetName, onNameChange, onAdd, error }: AddTargetSectionProps) => {
  return (
    <>
      <div className="flex mt-4">
        <input
          type="text"
          className="form-input flex-1"
          value={newTargetName}
          onChange={(e) => {
            onNameChange(e.target.value);
          }}
          placeholder="Enter target filename (e.g., service_k8s.json)"
        />
        <Button variant="primary" onClick={onAdd}>
          Add Target
        </Button>
      </div>
      {error && (
        <div className="error-message">{error}</div>
      )}
    </>
  );
};
