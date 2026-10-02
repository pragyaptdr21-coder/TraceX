import { useSearchParams } from 'react-router-dom';
import InvestigationGraphTab from '../components/InvestigationGraphTab';

export default function GraphFullscreen() {
  const [searchParams] = useSearchParams();
  const accountId = searchParams.get('q') || '';
  const rawHops = Number(searchParams.get('h'));
  const initialHops = [1, 2, 3, 4].includes(rawHops) ? rawHops : 4;

  return (
    <div className="graph-fullscreen">
      <InvestigationGraphTab initialAccountId={accountId} initialHops={initialHops} fullscreen />
    </div>
  );
}
