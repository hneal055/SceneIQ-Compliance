import { useCallback, useState } from 'react';
import UploadPanel, { type UploadSummary } from './UploadPanel';
import ResultsTable from './ResultsTable';

export default function ScheduleParser() {
  // bump this number to force the ResultsTable to refetch after a successful upload
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUploaded = useCallback((_summary: UploadSummary) => {
    setRefreshKey((n) => n + 1);
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Schedule Parser</h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload broadcast schedule files (CSV, XML/BXF, JSON) and review parsed segments.
        </p>
      </header>

      <UploadPanel onUploaded={handleUploaded} />
      <ResultsTable refreshKey={refreshKey} />
    </div>
  );
}
