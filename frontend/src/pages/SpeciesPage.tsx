import { useEffect, useState } from 'react';
import './SpeciesPage.css';

interface Species {
  id?: number;
  name: string;
  commonName: string;
  description: string;
  active: boolean;
}

function SpeciesPage() {
  const [species, setSpecies] = useState<Species[]>([]);
  const [newSpecies, setNewSpecies] = useState<Species>({
    name: '',
    commonName: '',
    description: '',
    active: true
  });

  useEffect(() => {
    fetchSpecies();
  }, []);

  const fetchSpecies = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/species');
      const data = await response.json();
      setSpecies(data);
    } catch (error) {
      console.error('Error fetching species:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetch('http://localhost:8080/api/species', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSpecies)
      });
      setNewSpecies({ name: '', commonName: '', description: '', active: true });
      fetchSpecies();
    } catch (error) {
      console.error('Error creating species:', error);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await fetch(`http://localhost:8080/api/species/${id}`, { method: 'DELETE' });
      fetchSpecies();
    } catch (error) {
      console.error('Error deleting species:', error);
    }
  };

  return (
    <div className="species-page">
      <h1>Species Management</h1>

      <form onSubmit={handleSubmit} className="species-form">
        <h2>Add New Species</h2>
        <input
          type="text"
          placeholder="Scientific Name (e.g., Panthera leo)"
          value={newSpecies.name}
          onChange={(e) => setNewSpecies({...newSpecies, name: e.target.value})}
          required
        />
        <input
          type="text"
          placeholder="Common Name (e.g., African Lion)"
          value={newSpecies.commonName}
          onChange={(e) => setNewSpecies({...newSpecies, commonName: e.target.value})}
        />
        <textarea
          placeholder="Description"
          value={newSpecies.description}
          onChange={(e) => setNewSpecies({...newSpecies, description: e.target.value})}
        />
        <button type="submit">Add Species</button>
      </form>

      <div className="species-grid">
        {species.map((s) => (
          <div key={s.id} className="species-card">
            <h3>{s.commonName || s.name}</h3>
            <p className="scientific-name">{s.name}</p>
            <p>{s.description}</p>
            <button onClick={() => s.id && handleDelete(s.id)} className="delete-btn">
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default SpeciesPage;
