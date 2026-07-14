import { ArrowRight, CalendarDays } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from './Button';
import { Modal } from './Modal';

interface NewSprintModalProps {
  open: boolean;
  onClose: () => void;
  onCreate: (name: string, startDate: string, duration: string) => void;
}

export function NewSprintModal({ open, onClose, onCreate }: NewSprintModalProps) {
  const [name, setName] = useState('Cloud Operations Sprint 25');
  const [startDate, setStartDate] = useState('2026-07-28');
  const [duration, setDuration] = useState('10');

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim() || !startDate) return;
    onCreate(name.trim(), startDate, duration);
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create a new sprint"
      description="Start with a clear goal, dates, and a realistic planning window."
      size="sm"
    >
      <form className="stack-form" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Sprint name</span>
          <input value={name} onChange={(event) => setName(event.target.value)} required />
        </label>
        <div className="form-grid form-grid--two">
          <label className="field">
            <span className="field__label">Start date</span>
            <span className="input-with-icon">
              <CalendarDays size={17} />
              <input
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                required
              />
            </span>
          </label>
          <label className="field">
            <span className="field__label">Duration</span>
            <select value={duration} onChange={(event) => setDuration(event.target.value)}>
              <option value="5">5 working days</option>
              <option value="10">10 working days</option>
              <option value="15">15 working days</option>
            </select>
          </label>
        </div>
        <div className="modal__footer">
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" type="submit" trailingIcon={<ArrowRight size={17} />}>
            Create sprint
          </Button>
        </div>
      </form>
    </Modal>
  );
}
