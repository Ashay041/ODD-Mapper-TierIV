// src/IntroPage.js
import React, { useState } from 'react';
import './IntroPage.css';

// Get backend configuration from environment variables
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://127.0.0.1';
const BACKEND_PORT = process.env.REACT_APP_BACKEND_PORT || '5000';
const API_BASE_URL = `${BACKEND_URL}:${BACKEND_PORT}`;

export default function IntroPage({ onSubmit }) {
  const [inputType, setInputType] = useState('PLACE');
  const [bbox,    setBbox]    = useState({ min_lon:'',min_lat:'',max_lon:'',max_lat:'' });
  const [point,   setPoint]   = useState({ lat:'',lon:'',distance:'' });
  const [address, setAddress] = useState({ address:'',distance:'' });
  const [place,   setPlace]   = useState('');
  const [overwrite,    setOverwrite]    = useState(false);
  const [defaultQuery, setDefaultQuery] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // build request body
    var payload = {
      input_type:     inputType,
      lane_width:     3.5,
      overwrite,
      default_query:  defaultQuery,
      // input and dist filled below
    };
    if (inputType === 'BBOX') {
      payload.input = [
        parseFloat(bbox.min_lon),
        parseFloat(bbox.min_lat),
        parseFloat(bbox.max_lon),
        parseFloat(bbox.max_lat),
      ];
    } else if (inputType === 'POINT') {
      payload.input = [ parseFloat(point.lat), parseFloat(point.lon) ];
      payload.dist  = parseFloat(point.distance);
    } else if (inputType === 'ADDRESS') {
      payload.input = address.address;
      payload.dist  = parseFloat(address.distance);
    } else { // PLACE
      payload.input = place;
    }
    if(defaultQuery) {
      payload = {
        default_query: defaultQuery
      };
    }

    try {
      const res = await fetch(`${API_BASE_URL}/query`, {
        method: 'POST',
        headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify(payload),
      });
      const results = await res.json();
      if (!res.ok) {
        throw new Error(`Server ${res.status}: ${JSON.stringify(results)}`);
      }

      // decide what to send up to App.js
      if (defaultQuery) {
        // server tells us exactly what it ran
        const { input_type, input, dist } = results;
        switch (input_type) {
          case 'BBOX': {
            const [min_lon, min_lat, max_lon, max_lat] = input;
            onSubmit({
              type: 'BBOX',
              bbox: { min_lon, min_lat, max_lon, max_lat }
            });
            break;
          }
          case 'POINT': {
            const [lat, lon] = input;
            onSubmit({
              type: 'POINT',
              lat: String(lat),
              lon: String(lon),
              distance: String(dist ?? '')
            });
            break;
          }
          case 'ADDRESS': {
            onSubmit({
              type: 'ADDRESS',
              address: input,
              distance: String(dist ?? '')
            });
            break;
          }
          case 'PLACE': {
            onSubmit({
              type: 'PLACE',
              place: input
            });
            break;
          }
          default:
            console.warn('Unknown input_type from server:', input_type);
        }
      } else {
        // just use the form values
        if (inputType === 'BBOX') {
          onSubmit({ type: 'BBOX',    bbox });
        } else if (inputType === 'POINT') {
          onSubmit({ type: 'POINT',   ...point });
        } else if (inputType === 'ADDRESS') {
          onSubmit({ type: 'ADDRESS', ...address });
        } else {
          onSubmit({ type: 'PLACE',   place });
        }
      }
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="intro-container">
      <form className="intro-form" onSubmit={handleSubmit}>
        <h1>ODD Visualization</h1>
        {error && <div className="error">{error}</div>}

        <fieldset>
          <legend>Input Type</legend>
          {['BBOX','POINT','ADDRESS','PLACE'].map(t => (
            <label key={t}>
              <input
                type="radio"
                name="inputType"
                value={t}
                checked={inputType===t}
                onChange={()=>setInputType(t)}
              />
              {{
                BBOX: 'Bounding Box',
                POINT: 'Point + Radius',
                ADDRESS: 'Address + Radius',
                PLACE: 'Place'
              }[t]}
            </label>
          ))}
        </fieldset>

        {inputType==='BBOX' && (
          <div className="grid">
            <label>
              Min Lon<input required type="number" step="any"
                value={bbox.min_lon}
                onChange={e=>setBbox({ ...bbox, min_lon: e.target.value })}
              />
            </label>
            <label>
              Min Lat<input required type="number" step="any"
                value={bbox.min_lat}
                onChange={e=>setBbox({ ...bbox, min_lat: e.target.value })}
              />
            </label>
            <label>
              Max Lon<input required type="number" step="any"
                value={bbox.max_lon}
                onChange={e=>setBbox({ ...bbox, max_lon: e.target.value })}
              />
            </label>
            <label>
              Max Lat<input required type="number" step="any"
                value={bbox.max_lat}
                onChange={e=>setBbox({ ...bbox, max_lat: e.target.value })}
              />
            </label>
          </div>
        )}

        {inputType==='POINT' && (
          <div className="grid">
            <label>
              Lat<input required type="number" step="any"
                value={point.lat}
                onChange={e=>setPoint({ ...point, lat: e.target.value })}
              />
            </label>
            <label>
              Lon<input required type="number" step="any"
                value={point.lon}
                onChange={e=>setPoint({ ...point, lon: e.target.value })}
              />
            </label>
            <label className="full-width">
              Radius (m)<input required type="number"
                value={point.distance}
                onChange={e=>setPoint({ ...point, distance: e.target.value })}
              />
            </label>
          </div>
        )}

        {inputType==='ADDRESS' && (
          <>
            <label>
              Address<input required type="text"
                value={address.address}
                onChange={e=>setAddress({ ...address, address: e.target.value })}
              />
            </label>
            <label>
              Radius (m)<input required type="number"
                value={address.distance}
                onChange={e=>setAddress({ ...address, distance: e.target.value })}
              />
            </label>
          </>
        )}

        {inputType==='PLACE' && (
          <label className="full-width">
            Place<input required type="text"
              value={place}
              onChange={e=>setPlace(e.target.value)}
            />
          </label>
        )}

        <div className="checkbox-group">
          <label>
            <input
              type="checkbox"
              checked={overwrite}
              onChange={e=>setOverwrite(e.target.checked)}
            /> Overwrite existing data
          </label>
          <label>
            <input
              type="checkbox"
              checked={defaultQuery}
              onChange={e=>setDefaultQuery(e.target.checked)}
            /> Use default query settings
          </label>
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Loading…' : 'Submit'}
        </button>
      </form>
    </div>
  );
}
